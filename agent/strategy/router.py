"""
strategy/router.py -- Crypto regime -> strategy dispatcher.

Crypto regimes (NO US equity regimes):
  BULL_TREND   -> momentum long entry
  BEAR_TREND   -> close positions / cash
  ACCUMULATION -> mean-reversion buy the dip
  PUMP         -> breakout long entry with tight stop
  DUMP         -> emergency close all
  FLAT         -> hold cash
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
from loguru import logger

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from strategy.momentum import momentum_signal
from strategy.breakout import breakout_signal
from strategy.vwap_scalper import vwap_scalper_signal


def route(regime: str, symbol: str, bars: pd.DataFrame, open_position: bool = False) -> dict:
    base = {"symbol": symbol, "regime": regime, "action": "HOLD", "strategy": "none", "reason": ""}

    if regime == "BULL_TREND":
        sig = momentum_signal(bars, direction="bull")
        return {**base, **sig}

    elif regime == "BEAR_TREND":
        if open_position:
            return {**base, "strategy": "momentum", "action": "CLOSE",
                    "reason": "BEAR_TREND -- closing long to protect capital"}
        return {**base, "strategy": "momentum", "action": "HOLD",
                "reason": "BEAR_TREND -- staying in cash"}

    elif regime == "RANGE":
        sig = vwap_scalper_signal(bars, open_position=open_position)
        return {**base, **sig}

    elif regime == "BREAKOUT":
        sig = breakout_signal(bars, direction="up")
        return {**base, **sig}

    else:  # FLAT
        return {**base, "strategy": "flat", "action": "HOLD",
                "reason": "FLAT regime -- waiting for clear signal"}
