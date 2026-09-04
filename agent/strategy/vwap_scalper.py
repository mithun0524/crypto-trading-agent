"""
strategy/vwap_scalper.py — VWAP Exhaustion Scalping Strategy.

Physics-based algorithmic approach:
Volume Weighted Average Price (VWAP) acts as the intraday "center of mass".
When the price moves far away from the VWAP (measured by Z-score), it stretches 
like a rubber band. If the price is stretched far while volume is dropping 
(kinetic energy is exhausted), the price snaps back to the mean.

Entry  : VWAP Z-Score < -2.5 AND vol_ratio < 0.8 (Exhausted drop) -> BUY
Exit   : VWAP Z-Score > 0.0 (Reverted to mean) -> CLOSE
"""
from __future__ import annotations

import pandas as pd


# Thresholds for Elasticity (Dynamic Percentiles)
Z_PCT_THRESHOLD   = 0.05  # Bottom 5% of recent Z-scores
VOL_PCT_THRESHOLD = 0.25  # Bottom 25% of recent volume (Exhaustion)
LOOKBACK_BARS     = 60    # Rolling window (e.g., 60 minutes)

def vwap_scalper_signal(bars: pd.DataFrame, open_position: bool = False) -> dict:
    """
    Generate a scalping signal based on dynamic VWAP elasticity and volume exhaustion.

    Parameters
    ----------
    bars          : OHLCV + feature DataFrame, most recent bar last
    open_position : whether we currently hold this symbol
    """
    if len(bars) < LOOKBACK_BARS:
        return {"strategy": "vwap_scalper", "action": "HOLD", "reason": "insufficient bars for percentiles"}

    window = bars.tail(LOOKBACK_BARS)
    curr = window.iloc[-1]

    zscore    = curr.get("vwap_zscore", 0.0)
    vol_ratio = curr.get("vol_ratio", 1.0)

    if pd.isna(zscore) or pd.isna(vol_ratio):
        return {"strategy": "vwap_scalper", "action": "HOLD", "reason": "indicators not ready"}

    # Dynamically calculate the extreme thresholds based on the recent market state
    dynamic_z_oversold = window["vwap_zscore"].quantile(Z_PCT_THRESHOLD)
    dynamic_vol_exhaust = window["vol_ratio"].quantile(VOL_PCT_THRESHOLD)
    
    # Momentum Divergence: RSI should be rising from oversold to confirm snap-back
    rsi_now = curr.get("rsi", 50.0)
    rsi_prev = window.iloc[-2].get("rsi", 50.0) if len(window) > 1 else 50.0
    rsi_bullish = (rsi_now > rsi_prev) and (rsi_now < 45.0)

    # Oversold + Volume Exhausted + Bullish Momentum → Buy the rubber band snap
    if zscore <= dynamic_z_oversold and vol_ratio <= dynamic_vol_exhaust and rsi_bullish:
        return {
            "strategy": "vwap_scalper",
            "action":   "BUY",
            "reason":   f"Exhaustion snap: Z={zscore:.2f} (<= {dynamic_z_oversold:.2f}), Vol={vol_ratio:.2f}, RSI={rsi_now:.1f}",
        }

    # Reverted to Mean OR Trailing Stop (RSI > 70 overbought) → Close the scalp
    if open_position:
        if zscore >= 0.0:
            return {
                "strategy": "vwap_scalper",
                "action":   "CLOSE",
                "reason":   f"Mean reversion exit: Z={zscore:.2f}",
            }
        elif rsi_now > 70.0:
            return {
                "strategy": "vwap_scalper",
                "action":   "CLOSE",
                "reason":   f"Trailing stop (Overbought): RSI={rsi_now:.1f}",
            }

    return {
        "strategy": "vwap_scalper",
        "action":   "HOLD",
        "reason":   f"Waiting: Z={zscore:.2f} (Target < {dynamic_z_oversold:.2f})",
    }
