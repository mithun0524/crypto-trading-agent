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


def label_regime(bars: pd.DataFrame) -> pd.Series:
    fwd  = bars["close"].pct_change(LABEL_HORIZON).shift(-LABEL_HORIZON)
    logr = np.log(bars["close"] / bars["close"].shift(1))
    vol  = logr.rolling(24).std() * np.sqrt(365 * 24)

    labels = pd.Series("FLAT", index=bars.index)
    labels[fwd >  TREND_RETURN_PCT * 2.5]                                      = "PUMP"
    labels[fwd < -TREND_RETURN_PCT * 2.5]                                      = "DUMP"
    labels[(fwd >  TREND_RETURN_PCT) & (labels == "FLAT")]                     = "BULL_TREND"
    labels[(fwd < -TREND_RETURN_PCT) & (labels == "FLAT")]                     = "BEAR_TREND"
    labels[(vol < VOL_THRESHOLD) & (labels == "FLAT") & (fwd.abs() < TREND_RETURN_PCT * 0.4)] = "ACCUMULATION"
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
