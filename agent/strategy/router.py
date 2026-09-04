"""
strategy/router.py -- Crypto regime -> Pure ML trading dispatcher.

Crypto regimes (predicted directly by XGBoost):
  BULL_TREND   -> BUY (Model learned profit target is likely)
  BEAR_TREND   -> CLOSE (Model learned stop loss is likely)
  BREAKOUT     -> BUY (Model learned squeeze expansion)
  DUMP         -> CLOSE (Model learned crash)
  RANGE / FLAT -> HOLD
"""
from __future__ import annotations
import pandas as pd
from loguru import logger

def route(regime: str, symbol: str, bars: pd.DataFrame, open_position: bool = False) -> dict:
    base = {"symbol": symbol, "regime": regime, "action": "HOLD", "strategy": "pure_ml", "reason": ""}

    if regime in ("BULL_TREND", "BREAKOUT", "PUMP"):
        return {**base, "action": "BUY", "reason": f"AI predicted {regime} - Executing BUY"}

    elif regime in ("BEAR_TREND", "DUMP"):
        if open_position:
            return {**base, "action": "CLOSE", "reason": f"AI predicted {regime} - Closing position"}
        return {**base, "action": "HOLD", "reason": f"AI predicted {regime} - Staying in cash"}

    else:
        # FLAT, RANGE
        return {**base, "action": "HOLD", "reason": f"AI predicted {regime} - Holding"}

