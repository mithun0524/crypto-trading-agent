"""
model/train.py -- CryptoPaper XGBoost regime classifier.
"""
from __future__ import annotations
import datetime as dt
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.metrics import classification_report
from xgboost import XGBClassifier

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import SYMBOLS, MODELS_DIR, LABEL_HORIZON, TREND_RETURN_PCT, VOL_THRESHOLD
from data.history import download_bars
from data.sentiment import build_fng_series
from features.engineer import compute_features, feature_columns


def label_regime(df: pd.DataFrame) -> pd.Series:
    """
    Generate forward-looking regime labels from historical OHLCV bars.
    Uses FUTURE data — for training only. Never used at inference.
    """
    n  = LABEL_HORIZON
    close = df["close"]
    fwd_ret = close.shift(-n) / close - 1            # n-bar forward return
    log_ret = np.log(close / close.shift(1))
    realvol = log_ret.rolling(20).std() * np.sqrt(365 * 24)

    # Bollinger channel for RANGE detection
    bb_mid   = close.rolling(20).mean()
    bb_std   = close.rolling(20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std

    # Rolling Bollinger bandwidth for BREAKOUT detection (squeeze → expansion)
    bb_width    = (bb_upper - bb_lower) / bb_mid
    width_pct   = bb_width.rank(pct=True)
    width_low   = (width_pct < 0.2)           # squeeze
    width_spike = bb_width > bb_width.shift(n) * 1.5  # sharp expansion

    labels = pd.Series("FLAT", index=df.index, name="regime")

    # ── TRIPLE-BARRIER METHOD ────────────────────────────────────────────────
    if "atr" in df.columns:
        profit_target = 1.5 * df["atr"]
        stop_loss     = 1.5 * df["atr"]
    else:
        profit_target = close * TREND_RETURN_PCT
        stop_loss     = close * TREND_RETURN_PCT

    close_arr = close.values
    pt_arr = profit_target.values
    sl_arr = stop_loss.values
    trend_labels = np.full(len(close_arr), "FLAT", dtype=object)
    
    for i in range(len(close_arr) - n):
        c = close_arr[i]
        t_up = c + pt_arr[i]
        t_dn = c - sl_arr[i]
        
        for lag in range(1, n + 1):
            future_c = close_arr[i + lag]
            if future_c >= t_up:
                trend_labels[i] = "BULL_TREND"
                break
            elif future_c <= t_dn:
                trend_labels[i] = "BEAR_TREND"
                break

    labels = pd.Series(trend_labels, index=df.index, name="regime")

    # BREAKOUT: squeeze followed by expansion (overrides FLAT, not TREND)
    mask_break = width_low.shift(n) & width_spike
    labels[mask_break & (labels == "FLAT")] = "BREAKOUT"

    # RANGE: price stayed inside Bollinger channel for the next n bars
    stayed_in = True
    for lag in range(1, n + 1):
        stayed_in = stayed_in & (
            (close.shift(-lag) <= bb_upper) & (close.shift(-lag) >= bb_lower)
        )
    labels[stayed_in & (labels == "FLAT")] = "RANGE"

    return labels


def _sharpe(rets: pd.Series, ppy: int = 365 * 24) -> float:
    std = rets.std()
    return float(rets.mean() / std * np.sqrt(ppy)) if std > 0 else 0.0


def train(symbols: list[str] | None = None, interval: str = "1h") -> Path:
    if symbols is None:
        symbols = SYMBOLS

    logger.info("=" * 60)
    logger.info("  CryptoPaper Model Training")
    logger.info(f"  Pairs    : {', '.join(symbols)}")
    logger.info(f"  Interval : {interval}")
    logger.info("=" * 60)

    # 1. Sentiment data -------------------------------------------------------
    logger.info("Fetching Fear & Greed Index (730 days)...")
    fng = build_fng_series(None)
    logger.info(f"  Fear & Greed: {len(fng)} days loaded")

    # 2. Download bars --------------------------------------------------------
    logger.info("Downloading crypto OHLCV bars...")
    all_bars = download_bars(symbols=symbols, interval=interval, force=False)

    # 3. Build feature rows (one row per bar per symbol, integer row index) ---
    all_rows = []
    for sym, bars in all_bars.items():
        if len(bars) < 400:
            logger.warning(f"Skipping {sym}: {len(bars)} bars")
            continue
        logger.info(f"Engineering features for {sym} ({len(bars)} bars)...")
        feat = compute_features(bars, fng_series=fng)
        lbl  = label_regime(bars).reindex(feat.index)
        valid = lbl.notna()
        feat, lbl = feat[valid].copy(), lbl[valid].copy()

        # Store timestamp as a regular column, reset to integer index
        feat["_ts"]     = feat.index
        feat["_symbol"] = sym
        feat["_label"]  = lbl.values
        feat = feat.reset_index(drop=True)
        all_rows.append(feat)

    if not all_rows:
        raise RuntimeError("No valid feature frames!")

    # 4. Combine and sort chronologically ------------------------------------
    combined = pd.concat(all_rows, ignore_index=True)
    combined.sort_values("_ts", inplace=True)
    combined.reset_index(drop=True, inplace=True)

    avail = [c for c in feature_columns() if c in combined.columns]
    X = combined[avail].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    y = combined["_label"]

    unique = sorted(y.unique())
    lmap   = {r: i for i, r in enumerate(unique)}
    y_enc  = y.map(lmap).astype(int)

    logger.info(f"\nDataset: {len(X):,} rows x {len(avail)} features")
    logger.info(f"Regime distribution:\n{y.value_counts().to_string()}")

    # 5. Time-series 80/20 split (no shuffle) --------------------------------
    split   = int(len(X) * 0.80)
    X_tr, X_val = X.iloc[:split], X.iloc[split:]
    y_tr, y_val = y_enc.iloc[:split], y_enc.iloc[split:]
    logger.info(f"Train: {len(X_tr):,}  |  Val: {len(X_val):,}")

    # 6. XGBoost (heavily regularised for crypto noise) ----------------------
    logger.info("Training XGBoost...")
    model = XGBClassifier(
        n_estimators=800,
        max_depth=5,
        learning_rate=0.025,
        subsample=0.70,
        colsample_bytree=0.70,
        min_child_weight=15,
        gamma=0.3,
        reg_alpha=0.1,
        reg_lambda=1.5,
        random_state=42,
        eval_metric="mlogloss",
        early_stopping_rounds=60,
        n_jobs=-1,
        verbosity=0,
    )
    model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)
    logger.success(f"Best iteration: {model.best_iteration}")

    # 7. Evaluate ------------------------------------------------------------
    y_pred = model.predict(X_val)
    rmap   = {v: k for k, v in lmap.items()}
    y_vn   = [rmap.get(i, "FLAT") for i in y_val]
    y_pn   = [rmap.get(i, "FLAT") for i in y_pred]
    logger.info(f"\nClassification report:\n{classification_report(y_vn, y_pn, zero_division=0)}")

    # Approx Sharpe
    fwd_ret = X_val["ret_1b"].shift(-1).fillna(0).values
    preds   = np.array(y_pn)
    sr      = np.zeros(len(preds))
    sr[np.isin(preds, ["BULL_TREND","PUMP"])]  =  fwd_ret[np.isin(preds, ["BULL_TREND","PUMP"])]
    sr[np.isin(preds, ["BEAR_TREND","DUMP"])]  = -fwd_ret[np.isin(preds, ["BEAR_TREND","DUMP"])]
    sharpe = _sharpe(pd.Series(sr))
    logger.info(f"Validation Sharpe: {sharpe:.3f}")

    # Top features
    fi = pd.Series(model.feature_importances_, index=avail).sort_values(ascending=False)
    logger.info(f"\nTop-10 features:\n{fi.head(10).to_string()}")

    # 8. Save ----------------------------------------------------------------
    version = dt.datetime.now().strftime("%Y%m%d_%H%M")
    mpath   = MODELS_DIR / f"regime_model_{version}.pkl"
    latest  = MODELS_DIR / "regime_model_latest.pkl"
    payload = {
        "model": model, "feature_cols": avail, "label_map": lmap,
        "version": version, "trained_at": dt.datetime.utcnow().isoformat(),
        "val_sharpe": sharpe, "symbols": symbols, "interval": interval,
    }
    with open(mpath, "wb") as f:
        pickle.dump(payload, f)
    import shutil; shutil.copy2(mpath, latest)
    logger.success(f"Model saved -> {mpath.name}  (Sharpe={sharpe:.3f})")
    return latest


if __name__ == "__main__":
    train()
