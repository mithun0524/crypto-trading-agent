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
from strategy.mean_reversion import mean_reversion_signal
from strategy.breakout import breakout_signal


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

    elif regime == "ACCUMULATION":
        # Accumulation = range-bound consolidation, buy dips aggressively
        sig = mean_reversion_signal(bars, aggressive=True)
        return {**base, **sig}

    elif regime == "PUMP":
        # Explosive upside breakout with volume -- ride it with tight stop
        sig = breakout_signal(bars, direction="up")
        return {**base, **sig}

    elif regime == "DUMP":
        # Flash crash / liquidation cascade -- exit everything immediately
        if open_position:
            return {**base, "strategy": "risk", "action": "CLOSE",
                    "reason": "DUMP detected -- emergency exit"}
        return {**base, "strategy": "risk", "action": "HOLD",
                "reason": "DUMP -- no position, staying in cash"}

    else:  # FLAT
        return {**base, "strategy": "flat", "action": "HOLD",
                "reason": "FLAT regime -- waiting for clear signal"}
