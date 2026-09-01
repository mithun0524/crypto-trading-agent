"""
strategy/mean_reversion.py -- Crypto accumulation / dip-buying strategy.

Crypto accumulation zones show:
1. RSI < 35 (oversold) -- aggressive: < 40
2. Price below lower Bollinger Band (bb_pos < 0.2)
3. Volume drying up (vol_ratio < 0.8) = no more selling pressure
4. ADX < 20 = not a strong trend, just sideways chop

Exit: RSI > 60 OR price back at BB midpoint
"""
from __future__ import annotations
import pandas as pd

RSI_BUY_NORMAL     = 35.0
RSI_BUY_AGGRESSIVE = 42.0
RSI_SELL           = 62.0
BB_BUY_ZONE        = 0.25
BB_SELL_ZONE       = 0.55


def mean_reversion_signal(bars: pd.DataFrame, aggressive: bool = False) -> dict:
    if len(bars) < 1:
        return {"strategy": "mean_reversion", "action": "HOLD", "reason": "insufficient bars"}

    curr = bars.iloc[-1]
    rsi     = curr.get("rsi", 50.0)
    bb_pos  = curr.get("bb_pos", 0.5)
    adx     = curr.get("adx", 20.0)
    vol_ratio = curr.get("vol_ratio", 1.0)

    if pd.isna(rsi) or pd.isna(bb_pos):
        return {"strategy": "mean_reversion", "action": "HOLD", "reason": "indicators not ready"}

    rsi_threshold = RSI_BUY_AGGRESSIVE if aggressive else RSI_BUY_NORMAL

    # Dip buy: oversold + near BB lower + low ADX (sideways) + volume dry
    if rsi < rsi_threshold and bb_pos < BB_BUY_ZONE and adx < 30:
        return {
            "strategy": "mean_reversion",
            "action": "BUY",
            "reason": f"Accumulation dip: RSI={rsi:.1f} bb_pos={bb_pos:.2f} ADX={adx:.1f}",
        }

    # Exit: recovered to midpoint
    if rsi > RSI_SELL or bb_pos > BB_SELL_ZONE:
        return {
            "strategy": "mean_reversion",
            "action": "CLOSE",
            "reason": f"Mean reversion complete: RSI={rsi:.1f} bb_pos={bb_pos:.2f}",
        }

    return {
        "strategy": "mean_reversion",
        "action": "HOLD",
        "reason": f"Waiting for deeper dip: RSI={rsi:.1f} bb_pos={bb_pos:.2f}",
    }
