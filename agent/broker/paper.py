"""
broker/paper.py â€” Paper trading broker.

Handles:
  - Position sizing (ATR-based fixed-fractional)
  - Next-bar-open order fills
  - Slippage and commission model
  - Daily circuit-breaker (halt if down > DAILY_LOSS_LIMIT_PCT)
  - P&L tracking
  - Risk limits (max positions, max size per position)
"""
from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from loguru import logger

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    STARTING_CASH, RISK_PER_TRADE_PCT, MAX_POSITION_PCT,
    MAX_OPEN_POSITIONS, DAILY_LOSS_LIMIT_PCT,
    SLIPPAGE_PCT, COMMISSION_PCT,
)


# â”€â”€ Data structures â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@dataclass
class Position:
    symbol:      str
    qty:         float
    entry_price: float
    entry_ts:    dt.datetime
    strategy:    str
    side:        str = "LONG"

    def unrealized_pnl(self, current_price: float) -> float:
        return (current_price - self.entry_price) * self.qty

    def market_value(self, current_price: float) -> float:
        return current_price * self.qty


@dataclass
class Trade:
    id:          str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol:      str = ""
    entry_ts:    Optional[dt.datetime] = None
    entry_price: float = 0.0
    exit_ts:     Optional[dt.datetime] = None
    exit_price:  float = 0.0
    qty:         float = 0.0
    side:        str = "LONG"
    strategy:    str = ""
    pnl:         float = 0.0
    commission:  float = 0.0


# â”€â”€ Paper Broker â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class PaperBroker:
    """
    Simulates a paper trading broker with realistic fill mechanics.
    All orders fill at the NEXT bar's open price to avoid lookahead bias.
    """

    def __init__(self, starting_cash: float = STARTING_CASH):
        self.cash:            float              = starting_cash
        self.starting_equity: float              = starting_cash
        self.positions:       dict[str, Position] = {}
        self.closed_trades:   list[Trade]        = []
        self.pending_orders:  list[dict]         = []   # filled next bar
        self._day_start_equity: float            = starting_cash
        self._halted:         bool               = False

    # â”€â”€ Equity â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def total_equity(self, prices: dict[str, float]) -> float:
        pos_value = sum(
            pos.market_value(prices.get(sym, pos.entry_price))
            for sym, pos in self.positions.items()
        )
        return self.cash + pos_value

    def positions_value(self, prices: dict[str, float]) -> float:
        return sum(
            pos.market_value(prices.get(sym, pos.entry_price))
            for sym, pos in self.positions.items()
        )

    def snapshot(self, prices: dict[str, float]) -> dict:
        equity = self.total_equity(prices)
        return {
            "cash":             round(self.cash, 2),
            "positions_value":  round(self.positions_value(prices), 2),
            "total_equity":     round(equity, 2),
            "open_positions":   len(self.positions),
            "pnl":              round(equity - self.starting_equity, 2),
            "pnl_pct":          round((equity / self.starting_equity - 1) * 100, 2),
        }

    # â”€â”€ Circuit breaker â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def reset_day(self, prices: dict[str, float]):
        """Call at start of each trading day to reset the daily loss counter."""
        self._day_start_equity = self.total_equity(prices)
        self._halted           = False

    def check_circuit_breaker(self, prices: dict[str, float]) -> bool:
        """Return True if daily loss limit is hit (new trades halted)."""
        if self._halted:
            return True
        equity    = self.total_equity(prices)
        daily_loss = (self._day_start_equity - equity) / self._day_start_equity
        if daily_loss >= DAILY_LOSS_LIMIT_PCT:
            logger.warning(
                f"ðŸ›‘ Circuit breaker triggered: daily loss {daily_loss*100:.2f}% "
                f"â‰¥ {DAILY_LOSS_LIMIT_PCT*100:.1f}%. Halting new trades."
            )
            self._halted = True
        return self._halted

    # â”€â”€ Position sizing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _size_position(self, price: float, atr: float, equity: float) -> float:
        """
        ATR-based fixed-fractional sizing.
        Risk RISK_PER_TRADE_PCT of equity on each trade.
        Stop = 1 ATR below entry. Shares = risk_amount / ATR.
        Also capped at MAX_POSITION_PCT * equity.
        """
        if atr <= 0:
            atr = price * 0.005   # fallback: 0.5% of price

        risk_amount    = equity * RISK_PER_TRADE_PCT
        qty_risk       = risk_amount / atr
        qty_max        = (equity * MAX_POSITION_PCT) / price
        qty            = min(qty_risk, qty_max)
        return max(1.0, round(qty, 2))

    # â”€â”€ Order placement â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def place_order(
        self,
        signal: dict,
        current_bar: dict,
        prices: dict[str, float],
        model_version: str = "unknown",
    ) -> dict | None:
        """
        Queue an order. Returns the order dict, or None if rejected.
        Orders fill at next bar's open (called in fill_pending_orders).
        """
        symbol   = signal["symbol"]
        action   = signal["action"]
        strategy = signal["strategy"]
        equity   = self.total_equity(prices)

        # â”€â”€ Rejection checks â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if action == "HOLD":
            return None

        if action == "BUY":
            if self.check_circuit_breaker(prices):
                logger.debug(f"  [{symbol}] BUY rejected â€” circuit breaker active")
                return None
            if symbol in self.positions:
                logger.debug(f"  [{symbol}] BUY rejected â€” position already open")
                return None
            if len(self.positions) >= MAX_OPEN_POSITIONS:
                logger.debug(f"  [{symbol}] BUY rejected â€” max positions ({MAX_OPEN_POSITIONS}) reached")
                return None

            atr = current_bar.get("atr", 0.0)
            qty = self._size_position(current_bar["close"], atr, equity)
            cost = qty * current_bar["close"] * (1 + SLIPPAGE_PCT)
            if cost > self.cash:
                logger.debug(f"  [{symbol}] BUY rejected â€” insufficient cash (need ${cost:.0f}, have ${self.cash:.0f})")
                return None

        elif action in ("SELL", "CLOSE"):
            if symbol not in self.positions:
                return None   # nothing to close

        order = {
            "symbol":        symbol,
            "action":        action,
            "strategy":      strategy,
            "regime":        signal.get("regime", ""),
            "reason":        signal.get("reason", ""),
            "model_version": model_version,
            "queued_price":  current_bar["close"],
            "queued_atr":    current_bar.get("atr", 0.0),
            "queued_equity": equity,
        }
        self.pending_orders.append(order)
        logger.debug(f"  [{symbol}] Order queued: {action} ({strategy})")
        return order

    # â”€â”€ Order fill (next bar's open) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def fill_pending_orders(
        self,
        next_bar: dict,
        ts: dt.datetime,
        prices: dict[str, float],
    ) -> list[Trade | None]:
        """
        Fill all pending orders at next bar's open price.
        Called at the start of each bar before signal generation.
        """
        filled: list[Trade | None] = []
        for order in self.pending_orders:
            symbol = order["symbol"]
            fill_price = next_bar.get("open", order["queued_price"])
            result = self._execute(order, fill_price, ts, prices)
            filled.append(result)
        self.pending_orders.clear()
        return filled

    def _execute(
        self,
        order: dict,
        fill_price: float,
        ts: dt.datetime,
        prices: dict[str, float],
    ) -> Trade | None:
        symbol   = order["symbol"]
        action   = order["action"]
        strategy = order["strategy"]
        equity   = self.total_equity(prices)

        if action == "BUY":
            qty        = self._size_position(fill_price, order["queued_atr"], equity)
            slip_price = fill_price * (1 + SLIPPAGE_PCT)
            commission = (qty * slip_price) * COMMISSION_PCT
            cost       = qty * slip_price + commission

            if cost > self.cash:
                logger.warning(f"  [{symbol}] BUY fill failed â€” insufficient cash at fill time")
                return None

            self.cash -= cost
            self.positions[symbol] = Position(
                symbol=symbol,
                qty=qty,
                entry_price=slip_price,
                entry_ts=ts,
                strategy=strategy,
            )
            logger.info(
                f"  âœ… BUY  {symbol} {qty:.2f} @ ${slip_price:.2f} "
                f"(cost ${cost:.0f}, cash left ${self.cash:.0f})"
            )
            return None   # open trade â€” no closed Trade yet

        elif action in ("SELL", "CLOSE"):
            if symbol not in self.positions:
                return None

            pos        = self.positions.pop(symbol)
            slip_price = fill_price * (1 - SLIPPAGE_PCT)
            commission = (pos.qty * slip_price) * COMMISSION_PCT
            proceeds   = pos.qty * slip_price - commission
            pnl        = proceeds - pos.qty * pos.entry_price

            self.cash += proceeds

            trade = Trade(
                symbol=symbol,
                entry_ts=pos.entry_ts,
                entry_price=pos.entry_price,
                exit_ts=ts,
                exit_price=slip_price,
                qty=pos.qty,
                side=pos.side,
                strategy=strategy,
                pnl=round(pnl, 2),
                commission=round(commission * 2, 4),
            )
            self.closed_trades.append(trade)
            emoji = "ðŸŸ¢" if pnl > 0 else "ðŸ”´"
            logger.info(
                f"  {emoji} CLOSE {symbol} {pos.qty:.2f} @ ${slip_price:.2f} "
                f"P&L ${pnl:.2f} ({pnl/pos.entry_price/pos.qty*100:.2f}%)"
            )
            return trade

        return None

    def close_all(self, prices: dict[str, float], ts: dt.datetime) -> list[Trade]:
        """Force-close all open positions at current prices (EOD close)."""
        trades = []
        for symbol, pos in list(self.positions.items()):
            price = prices.get(symbol, pos.entry_price)
            order = {
                "symbol": symbol, "action": "CLOSE",
                "strategy": pos.strategy, "regime": "EOD",
                "reason": "EOD forced close", "model_version": "N/A",
                "queued_price": price, "queued_atr": 0.0, "queued_equity": 0.0,
            }
            t = self._execute(order, price, ts, prices)
            if t:
                trades.append(t)
        return trades

    # â”€â”€ Stats â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def stats(self) -> dict:
        trades = self.closed_trades
        if not trades:
            return {"total_trades": 0}
        pnls      = [t.pnl for t in trades]
        wins      = [p for p in pnls if p > 0]
        losses    = [p for p in pnls if p <= 0]
        return {
            "total_trades":  len(trades),
            "winners":       len(wins),
            "losers":        len(losses),
            "win_rate":      round(len(wins) / len(trades) * 100, 1) if trades else 0,
            "total_pnl":     round(sum(pnls), 2),
            "avg_win":       round(sum(wins) / len(wins), 2) if wins else 0,
            "avg_loss":      round(sum(losses) / len(losses), 2) if losses else 0,
            "profit_factor": round(-sum(wins) / sum(losses), 3) if losses and sum(losses) != 0 else 0,
        }


