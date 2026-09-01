"""
tests/test_broker.py — Unit tests for the paper broker.
"""
import datetime as dt
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from broker.paper import PaperBroker


def make_broker() -> PaperBroker:
    return PaperBroker(starting_cash=100_000.0)


def make_signal(symbol="SPY", action="BUY", strategy="trend", regime="TREND_UP"):
    return {"symbol": symbol, "action": action, "strategy": strategy,
            "regime": regime, "reason": "test"}


def make_bar(close=400.0, open_=399.0, atr=2.0):
    return {"close": close, "open": open_, "atr": atr}


# ── Buy / Sell cycle ──────────────────────────────────────────────────────────

def test_buy_creates_position():
    broker = make_broker()
    prices = {"SPY": 400.0}
    sig    = make_signal("SPY", "BUY")
    bar    = make_bar()

    order = broker.place_order(sig, bar, prices)
    assert order is not None
    assert len(broker.pending_orders) == 1

    # Fill at next bar's open
    broker.fill_pending_orders({"SPY": 401.0}, dt.datetime.utcnow(), prices)
    assert "SPY" in broker.positions
    assert broker.positions["SPY"].qty > 0


def test_close_removes_position_and_creates_trade():
    broker = make_broker()
    prices = {"SPY": 400.0}

    # Buy
    broker.place_order(make_signal("SPY", "BUY"), make_bar(), prices)
    broker.fill_pending_orders({"SPY": 401.0}, dt.datetime.utcnow(), prices)
    assert "SPY" in broker.positions

    # Close
    prices = {"SPY": 420.0}
    broker.place_order(make_signal("SPY", "CLOSE"), make_bar(close=420.0), prices)
    broker.fill_pending_orders({"SPY": 421.0}, dt.datetime.utcnow(), prices)

    assert "SPY" not in broker.positions
    assert len(broker.closed_trades) == 1
    assert broker.closed_trades[0].pnl > 0   # profitable trade


def test_winning_trade_pnl():
    broker = make_broker()
    prices = {"SPY": 400.0}
    broker.place_order(make_signal("SPY", "BUY"), make_bar(close=400.0, atr=2.0), prices)
    broker.fill_pending_orders({"SPY": 400.0}, dt.datetime.utcnow(), prices)

    prices = {"SPY": 450.0}
    broker.place_order(make_signal("SPY", "CLOSE"), make_bar(close=450.0), prices)
    broker.fill_pending_orders({"SPY": 450.0}, dt.datetime.utcnow(), prices)

    trade = broker.closed_trades[0]
    assert trade.pnl > 0
    assert trade.symbol == "SPY"


def test_losing_trade_pnl():
    broker = make_broker()
    prices = {"SPY": 400.0}
    broker.place_order(make_signal("SPY", "BUY"), make_bar(close=400.0, atr=2.0), prices)
    broker.fill_pending_orders({"SPY": 400.0}, dt.datetime.utcnow(), prices)

    prices = {"SPY": 350.0}
    broker.place_order(make_signal("SPY", "CLOSE"), make_bar(close=350.0), prices)
    broker.fill_pending_orders({"SPY": 350.0}, dt.datetime.utcnow(), prices)

    assert broker.closed_trades[0].pnl < 0


# ── Risk limits ───────────────────────────────────────────────────────────────

def test_max_positions_rejected():
    from config import MAX_OPEN_POSITIONS
    broker  = make_broker()
    symbols = [f"SYM{i}" for i in range(MAX_OPEN_POSITIONS + 2)]

    for sym in symbols[:MAX_OPEN_POSITIONS]:
        prices = {sym: 100.0}
        broker.place_order(make_signal(sym, "BUY"), make_bar(close=100.0, atr=1.0), prices)
        broker.fill_pending_orders({sym: 100.0}, dt.datetime.utcnow(), prices)

    # Next BUY should be rejected
    extra_sym = symbols[MAX_OPEN_POSITIONS]
    prices    = {extra_sym: 100.0}
    order     = broker.place_order(make_signal(extra_sym, "BUY"), make_bar(close=100.0), prices)
    assert order is None


def test_duplicate_position_rejected():
    broker = make_broker()
    prices = {"SPY": 400.0}
    broker.place_order(make_signal("SPY", "BUY"), make_bar(), prices)
    broker.fill_pending_orders({"SPY": 401.0}, dt.datetime.utcnow(), prices)

    # Second BUY on same symbol rejected
    order = broker.place_order(make_signal("SPY", "BUY"), make_bar(), prices)
    assert order is None


def test_circuit_breaker():
    from config import DAILY_LOSS_LIMIT_PCT, STARTING_CASH
    broker = make_broker()
    # Manually drain cash to simulate a big loss
    broker.cash = STARTING_CASH * (1 - DAILY_LOSS_LIMIT_PCT - 0.01)
    prices = {"SPY": 100.0}
    broker.reset_day({"SPY": 100.0})  # set day start to current (low) equity
    # Force equity below daily loss threshold
    broker.cash = STARTING_CASH * 0.5   # 50% loss
    assert broker.check_circuit_breaker({"SPY": 100.0}) is True


# ── Idempotency ───────────────────────────────────────────────────────────────

def test_hold_signal_not_queued():
    broker = make_broker()
    prices = {"SPY": 400.0}
    order  = broker.place_order(make_signal("SPY", "HOLD"), make_bar(), prices)
    assert order is None
    assert len(broker.pending_orders) == 0


def test_close_with_no_position_is_noop():
    broker = make_broker()
    prices = {"SPY": 400.0}
    order  = broker.place_order(make_signal("SPY", "CLOSE"), make_bar(), prices)
    assert order is None


# ── Stats ─────────────────────────────────────────────────────────────────────

def test_stats_empty():
    broker = make_broker()
    stats  = broker.stats()
    assert stats["total_trades"] == 0


def test_stats_win_rate():
    broker = make_broker()

    def _trade(sym, entry, exit_p):
        prices = {sym: entry}
        broker.place_order(make_signal(sym, "BUY"), make_bar(close=entry, atr=1.0), prices)
        broker.fill_pending_orders({sym: entry}, dt.datetime.utcnow(), prices)
        prices = {sym: exit_p}
        broker.place_order(make_signal(sym, "CLOSE"), make_bar(close=exit_p), prices)
        broker.fill_pending_orders({sym: exit_p}, dt.datetime.utcnow(), prices)

    _trade("SPY",  400, 420)   # win
    _trade("AAPL", 180, 170)   # loss

    stats = broker.stats()
    assert stats["total_trades"] == 2
    assert stats["winners"] == 1
    assert stats["losers"]  == 1
    assert stats["win_rate"] == 50.0
