"""
Fast Vectorized Backtest
Runs the XGBoost model over the entire feature set in one go, rather than simulating bar-by-bar latency.
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from data.history import download_bars
from features.engineer import compute_features, feature_columns
from model.predict import _load_model, MODELS_DIR

def run_fast_backtest():
    print("Loading model...")
    payload = _load_model(str(MODELS_DIR / "regime_model_latest.pkl"))
    model = payload["model"]
    feature_cols = payload["feature_cols"]
    rev_map = {v: k for k, v in payload["label_map"].items()}

    print("Loading data...")
    all_bars = download_bars(interval="1h", force=False)
    
    total_pnl = 0.0
    wins = 0
    losses = 0

    print("Running vectorised inference...")
    for sym, bars in all_bars.items():
        if sym.startswith("^"): continue
        if len(bars) < 300: continue
        
        feat = compute_features(bars, vix_level=18.0, vix_roc=0.0)
        # Prepare X matrix
        available_cols = [c for c in feature_cols if c in feat.columns]
        X = feat[available_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)
        
        # Predict all rows at once
        preds = model.predict(X)
        regimes = [rev_map.get(int(p), "FLAT") for p in preds]
        
        # Align with forward returns
        feat["regime"] = regimes
        feat["fwd_ret"] = feat["close"].pct_change().shift(-1)
        
        # Apply simple strategy:
        # Long on TREND_UP / BREAKOUT
        # TREND_DOWN is just holding cash (return 0)
        long_mask = feat["regime"].isin(["TREND_UP", "BREAKOUT"])
        
        feat["strat_ret"] = 0.0
        feat.loc[long_mask, "strat_ret"] = feat["fwd_ret"]
        
        sym_pnl = feat["strat_ret"].sum()
        total_pnl += sym_pnl
        
        trades = feat[feat["strat_ret"] != 0]["strat_ret"]
        wins += (trades > 0).sum()
        losses += (trades < 0).sum()
        
        print(f"  {sym:>4}: {sym_pnl*100:>6.2f}% return (from {len(trades)} trades)")
        
    print("-" * 40)
    print(f"Total Theoretical Return: {total_pnl*100:.2f}%")
    total_trades = wins + losses
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    print(f"Total Trades: {total_trades}")
    print(f"Win Rate: {win_rate:.1f}%")

if __name__ == "__main__":
    run_fast_backtest()
