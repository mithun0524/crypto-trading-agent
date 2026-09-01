"""
crypto_backtest.py -- ML-powered backtest using the trained XGBoost model.
"""
import sys, pickle
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from config import YFINANCE_SYMBOLS, STARTING_CASH, SLIPPAGE_PCT, MODELS_DIR
from data.history import download_bars
from data.sentiment import build_fng_series
from features.engineer import compute_features

def run_backtest():
    print("=" * 60)
    print("  CryptoPaper ML Backtest (Trained Model)")
    print("  Period: 2yr | 1h bars | Capital: $100,000")
    print("=" * 60)

    # Load model
    model_path = MODELS_DIR / "regime_model_latest.pkl"
    if not model_path.exists():
        print("No model found. Run training first.")
        return
    with open(model_path, "rb") as f:
        payload = pickle.load(f)
    model     = payload["model"]
    feat_cols = payload["feature_cols"]
    lmap      = payload["label_map"]
    rev_map   = {v: k for k, v in lmap.items()}
    print(f"\nModel: {payload['version']}  |  Val Sharpe: {payload['val_sharpe']:.3f}\n")

    # Fear & Greed
    fng = build_fng_series(None)

    # Download bars (use cached)
    print("[1] Loading bar data...")
    all_bars = download_bars(force=False)

    total_pnl   = 0.0
    all_wins    = 0
    all_losses  = 0
    all_trades  = 0
    results     = {}

    print("[2] Running ML inference + strategy simulation...")
    for sym, bars in all_bars.items():
        if len(bars) < 400:
            continue

        feat = compute_features(bars, fng_series=fng)
        avail = [c for c in feat_cols if c in feat.columns]
        X = feat[avail].replace([np.inf, -np.inf], np.nan).fillna(0.0)

        # Predict regimes for all bars at once
        preds_enc = model.predict(X)
        regimes   = [rev_map.get(int(p), "FLAT") for p in preds_enc]
        feat["regime"] = regimes

        # Forward return (next bar)
        feat["fwd_ret"] = feat["close"].pct_change(1).shift(-1)

        # Strategy:
        #   Long on BULL_TREND / PUMP (with slippage)
        #   Cash on BEAR_TREND / DUMP / FLAT
        #   Accumulation: small long (50% size)
        feat["signal"]   = 0.0
        feat.loc[feat["regime"].isin(["BULL_TREND", "PUMP"]),         "signal"] = 1.0
        feat.loc[feat["regime"] == "ACCUMULATION",                    "signal"] = 0.5
        feat.loc[feat["regime"].isin(["BEAR_TREND", "DUMP"]),         "signal"] = 0.0

        # Apply slippage on entry/exit changes
        sig_change = feat["signal"].diff().abs()
        feat["strat_ret"] = feat["signal"] * feat["fwd_ret"] - sig_change * SLIPPAGE_PCT

        # Allocate 25% of capital to each coin
        allocation    = STARTING_CASH * 0.25
        feat["pnl_$"] = feat["strat_ret"] * allocation

        sym_pnl   = feat["pnl_$"].sum()
        sym_ret   = feat["strat_ret"].sum() * 100
        sym_trades = int(sig_change.sum())
        trade_rets = feat.loc[feat["signal"] > 0, "strat_ret"]
        wins   = int((trade_rets > 0).sum())
        losses = int((trade_rets <= 0).sum())
        wr     = wins/(wins+losses)*100 if (wins+losses) > 0 else 0

        # Max drawdown
        cum = (1 + feat["strat_ret"].fillna(0)).cumprod()
        dd  = (cum - cum.cummax()) / cum.cummax()
        max_dd = dd.min() * 100

        # Sharpe (hourly)
        active = feat.loc[feat["signal"] > 0, "strat_ret"]
        sharpe = (active.mean()/active.std()*np.sqrt(365*24)) if active.std() > 0 else 0

        results[sym] = dict(pnl=sym_pnl, ret=sym_ret, trades=sym_trades,
                            wr=wr, dd=max_dd, sharpe=sharpe)
        total_pnl  += sym_pnl
        all_wins   += wins
        all_losses += losses
        all_trades += sym_trades

        # Regime breakdown
        rc = feat["regime"].value_counts()
        print(f"\n  {sym}")
        print(f"    P&L:      ${sym_pnl:>+10,.2f}  ({sym_ret:+.2f}%)")
        print(f"    Sharpe:   {sharpe:.3f}   MaxDD: {max_dd:.1f}%   WinRate: {wr:.1f}%")
        print(f"    Regimes:  " + "  ".join(f"{r}={rc.get(r,0)}" for r in ["BULL_TREND","PUMP","ACCUMULATION","FLAT","BEAR_TREND","DUMP"]))

    ending   = STARTING_CASH + total_pnl
    total_ret = total_pnl / STARTING_CASH * 100
    overall_wr = all_wins/(all_wins+all_losses)*100 if (all_wins+all_losses) > 0 else 0

    print("\n" + "=" * 60)
    print("  PORTFOLIO SUMMARY")
    print("=" * 60)
    print(f"  Starting Capital : ${STARTING_CASH:>12,.2f}")
    print(f"  Ending Equity    : ${ending:>12,.2f}")
    print(f"  Total P&L        : ${total_pnl:>+12,.2f}")
    print(f"  Total Return     : {total_ret:>+8.2f}%")
    print(f"  Total Trades     : {all_trades:>8,}")
    print(f"  Overall Win Rate : {overall_wr:>8.1f}%")
    print("=" * 60)

if __name__ == "__main__":
    run_backtest()
