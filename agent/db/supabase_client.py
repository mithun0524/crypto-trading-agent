"""
db/supabase_client.py -- CryptoPaper Supabase DB client.

All tables are prefixed with crypto_ to share the same Supabase project
as the US equities bot without any data collision.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

from loguru import logger

import time
import functools

def with_retry(max_retries=3, delay=1.0, backoff=2.0):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries:
                        logger.error(f"Supabase {func.__name__} failed after {max_retries} attempts: {e}")
                        raise
                    logger.warning(f"Supabase {func.__name__} attempt {attempt} failed ({e}). Retrying in {current_delay}s...")
                    
                    # Force recreate client on next retry by clearing the singleton
                    import sys
                    mod = sys.modules[__name__]
                    if hasattr(mod, '_client'):
                        mod._client = None
                        
                    time.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator


import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import SUPABASE_URL, SUPABASE_KEY

# -- Client singleton ---------------------------------------------------------

_client = None

def get_client():
    global _client
    if _client is None:
        from supabase import create_client
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


# -- Bar writes ---------------------------------------------------------------

@with_retry()
def upsert_bar(symbol: str, bar: dict) -> None:
    ts = bar["ts"]
    if isinstance(ts, dt.datetime):
        ts = ts.isoformat()
    row = {
        "symbol": symbol,
        "ts":     ts,
        "open":   round(float(bar["open"]),   6),
        "high":   round(float(bar["high"]),   6),
        "low":    round(float(bar["low"]),    6),
        "close":  round(float(bar["close"]),  6),
        "volume": int(bar.get("volume", 0)),
    }
    try:
        get_client().table("crypto_bars").upsert(row, on_conflict="symbol,ts").execute()
    except Exception as exc:
        logger.error(f"upsert_bar failed [{symbol}]: {exc}")


# -- Signal writes ------------------------------------------------------------

@with_retry()
def upsert_signal(
    symbol: str,
    ts: dt.datetime,
    regime: str,
    strategy: str,
    action: str,
    reason: str,
    model_version: str,
) -> None:
    row = {
        "symbol":    symbol,
        "ts":        ts.isoformat() if isinstance(ts, dt.datetime) else ts,
        "regime":    regime,
        "strategy":  strategy,
        "action":    action,
        "reason":    reason,
        "model_ver": model_version,
    }
    try:
        get_client().table("crypto_signals").upsert(row, on_conflict="symbol,ts").execute()
    except Exception as exc:
        logger.error(f"upsert_signal failed [{symbol}]: {exc}")


# -- Trade writes -------------------------------------------------------------

@with_retry()
def insert_trade(trade: Any) -> None:
    row = {
        "symbol":   trade.symbol,
        "ts":       trade.exit_ts.isoformat() if trade.exit_ts else dt.datetime.utcnow().isoformat(),
        "side":     trade.side,
        "qty":      round(float(trade.qty), 8),
        "price":    round(float(trade.exit_price), 6),
        "pnl":      round(float(trade.pnl), 4),
        "strategy": trade.strategy,
        "model_ver": getattr(trade, "model_version", "v1"),
    }
    try:
        get_client().table("crypto_trades").insert(row).execute()
    except Exception as exc:
        logger.error(f"insert_trade failed [{trade.symbol}]: {exc}")


# -- Equity curve writes ------------------------------------------------------

@with_retry()
def upsert_equity(ts: dt.datetime, snap: dict) -> None:
    row = {
        "ts":        ts.isoformat() if isinstance(ts, dt.datetime) else str(ts),
        "cash":      round(float(snap["cash"]), 2),
        "portfolio": round(float(snap.get("positions_value", 0)), 2),
        "total":     round(float(snap.get("total_equity", snap["cash"])), 2),
    }
    try:
        get_client().table("crypto_equity_curve").upsert(row, on_conflict="ts").execute()
    except Exception as exc:
        logger.error(f"upsert_equity failed: {exc}")


# -- Live quote writes --------------------------------------------------------

@with_retry()
def upsert_live_quote(
    symbol: str,
    last_price: float,
    change_pct: float = 0.0,
    volume: int = 0,
    regime: str = "FLAT",
) -> None:
    row = {
        "symbol":     symbol,
        "price":      round(float(last_price), 6),
        "change_pct": round(float(change_pct or 0.0), 4),
        "volume":     int(volume or 0),
        "regime":     regime,
        "updated_at": dt.datetime.utcnow().isoformat(),
    }
    try:
        get_client().table("crypto_live_quotes").upsert(row, on_conflict="symbol").execute()
    except Exception as exc:
        logger.error(f"upsert_live_quote failed [{symbol}]: {exc}")
