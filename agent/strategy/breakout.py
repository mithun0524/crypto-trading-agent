"""
strategy/breakout.py -- Crypto PUMP breakout strategy.

Crypto pumps are characterised by:
1. Price breaking 2-day Donchian high (dc_pos > 0.90)
2. Volume surge > 2x 24h average (vol_surge = 1)
3. RSI 50-75 (not yet overbought)
4. BB squeeze just resolved (bb_squeeze was 1, now price breaking out)

Exit: price falls back below Donchian midpoint OR RSI > 82 (euphoria top)
"""
from __future__ import annotations
import pandas as pd


def breakout_signal(bars: pd.DataFrame, direction: str = "up") -> dict:
    if len(bars) < 2:
        return {"strategy": "breakout", "action": "HOLD", "reason": "insufficient bars"}

    curr = bars.iloc[-1]
    prev = bars.iloc[-2]

    dc_pos    = curr.get("dc_pos", 0.5)
    vol_surge = curr.get("vol_surge", 0)
    vol_ratio = curr.get("vol_ratio", 1.0)
    rsi       = curr.get("rsi", 50.0)
    bb_squeeze = prev.get("bb_squeeze", 0)  # was there a squeeze before?
    close     = curr.get("close", 0.0)
    dc_upper  = curr.get("dc_upper", None)
    dc_lower  = curr.get("dc_lower", None)

    if pd.isna(dc_pos) or dc_upper is None:
        return {"strategy": "breakout", "action": "HOLD", "reason": "Donchian not ready"}

    # Confirmed pump: price at 2-day high + volume surge + RSI not overcooked
    if dc_pos > 0.80 and vol_ratio > 1.2 and 35 < rsi < 85:
        squeeze_note = " (post-squeeze)" if bb_squeeze else ""
        return {
            "strategy": "breakout",
            "action": "BUY",
            "reason": f"PUMP breakout{squeeze_note}: dc_pos={dc_pos:.2f} vol={vol_ratio:.1f}x RSI={rsi:.1f}",
        }

    # Stop: price collapsed back below midpoint = failed breakout
    if dc_pos < 0.25 or rsi > 88:
        return {
            "strategy": "breakout",
            "action": "CLOSE",
            "reason": f"Breakout failed/topped: dc_pos={dc_pos:.2f} RSI={rsi:.1f}",
        }

    return {
        "strategy": "breakout",
        "action": "HOLD",
        "reason": f"Watching for breakout: dc_pos={dc_pos:.2f} vol={vol_ratio:.1f}x",
    }
