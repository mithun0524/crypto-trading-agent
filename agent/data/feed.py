"""
data/feed.py -- CryptoPaper live data feed.

Tries Alpaca CryptoDataStream first; falls back to yfinance polling.
Crypto is 24/7 -- no market hours gate needed.
"""
from __future__ import annotations

import collections
import threading
import time
from typing import Callable

import pandas as pd
import yfinance as yf
from loguru import logger

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    SYMBOLS, YFINANCE_SYMBOLS, WARM_UP_BARS,
    ALPACA_API_KEY, ALPACA_API_SECRET,
)

BarCallback = Callable[[str, dict], None]


# -- Rolling bar buffer -------------------------------------------------------

class BarBuffer:
    """Fixed-length deque of bars per symbol."""

    def __init__(self, maxlen: int = 500):
        self._data: dict[str, collections.deque] = {
            s: collections.deque(maxlen=maxlen) for s in SYMBOLS
        }

    def push(self, symbol: str, bar: dict):
        if symbol not in self._data:
            self._data[symbol] = collections.deque(maxlen=500)
        self._data[symbol].append(bar)

    def ready(self, symbol: str, n: int) -> bool:
        return len(self._data.get(symbol, [])) >= n

    def to_dataframe(self, symbol: str) -> pd.DataFrame:
        bars = list(self._data.get(symbol, []))
        if not bars:
            return pd.DataFrame()
        df = pd.DataFrame(bars)
        df["ts"] = pd.to_datetime(df["ts"], utc=True)
        df.set_index("ts", inplace=True)
        df.sort_index(inplace=True)
        return df


# -- Alpaca Crypto WebSocket --------------------------------------------------

class AlpacaFeed:
    """Alpaca CryptoDataStream WebSocket feed."""

    def __init__(self, on_bar: BarCallback, buffer: BarBuffer):
        self.on_bar   = on_bar
        self.buffer   = buffer
        self._stream  = None
        self._running = False

    def start(self) -> bool:
        if not ALPACA_API_KEY or not ALPACA_API_SECRET:
            logger.warning("Alpaca keys missing. Falling back to yfinance polling.")
            return False

        try:
            from alpaca.data.live import CryptoDataStream

            self._stream = CryptoDataStream(
                api_key=ALPACA_API_KEY,
                secret_key=ALPACA_API_SECRET,
            )

            async def _bar_handler(bar):
                symbol = bar.symbol   # e.g. "BTC/USD"
                b = {
                    "ts":     bar.timestamp,
                    "open":   float(bar.open),
                    "high":   float(bar.high),
                    "low":    float(bar.low),
                    "close":  float(bar.close),
                    "volume": float(bar.volume),
                }
                self.buffer.push(symbol, b)
                self.on_bar(symbol, b)

            self._stream.subscribe_bars(_bar_handler, *SYMBOLS)

            self._thread = threading.Thread(
                target=self._stream.run,
                name="alpaca-crypto-ws",
                daemon=True,
            )
            self._thread.start()
            self._running = True
            logger.success(f"Alpaca Crypto WebSocket started for {len(SYMBOLS)} pairs")
            return True

        except Exception as exc:
            logger.error(f"Alpaca crypto stream failed: {exc}")
            return False

    def stop(self):
        if self._stream:
            try:
                self._stream.stop()
            except Exception:
                pass
        self._running = False


# -- yfinance fallback poller -------------------------------------------------

class YFinanceFallback:
    """60-second polling fallback using yfinance crypto tickers."""

    def __init__(self, on_bar: BarCallback, buffer: BarBuffer):
        self.on_bar   = on_bar
        self.buffer   = buffer
        self._running = False
        self._last_ts: dict[str, pd.Timestamp | None] = {s: None for s in SYMBOLS}

    def start(self):
        self._running = True
        self._thread  = threading.Thread(
            target=self._poll_loop,
            name="yfinance-crypto-fallback",
            daemon=True,
        )
        self._thread.start()
        logger.info("yfinance crypto fallback poller started")

    def stop(self):
        self._running = False

    def _poll_loop(self):
        while self._running:
            self._poll_once()
            time.sleep(60)

    def _poll_once(self):
        for sym in SYMBOLS:
            yf_sym = YFINANCE_SYMBOLS.get(sym, sym)
            try:
                raw = yf.download(
                    yf_sym,
                    period="1d",
                    interval="1m",
                    auto_adjust=True,
                    progress=False,
                    threads=False,
                )
                if raw.empty:
                    continue

                if isinstance(raw.columns, pd.MultiIndex):
                    raw.columns = raw.columns.get_level_values(0)

                raw.columns = [c.lower() for c in raw.columns]
                raw.index   = pd.to_datetime(raw.index, utc=True)
                raw.sort_index(inplace=True)

                last     = self._last_ts[sym]
                new_bars = raw if last is None else raw[raw.index > last]

                for ts, row in new_bars.iterrows():
                    b = {
                        "ts":     ts.to_pydatetime(),
                        "open":   float(row["open"]),
                        "high":   float(row["high"]),
                        "low":    float(row["low"]),
                        "close":  float(row["close"]),
                        "volume": float(row.get("volume", 0)),
                    }
                    self.buffer.push(sym, b)
                    self.on_bar(sym, b)
                    self._last_ts[sym] = ts

            except Exception as exc:
                logger.warning(f"yfinance crypto poll error [{sym}]: {exc}")


# -- Unified LiveFeed ---------------------------------------------------------

class LiveFeed:
    """
    Unified live feed. Tries Alpaca CryptoDataStream;
    falls back to yfinance polling.
    """

    def __init__(self, on_bar: BarCallback):
        self.buffer   = BarBuffer()
        self._alpaca  = AlpacaFeed(on_bar, self.buffer)
        self._yf      = YFinanceFallback(on_bar, self.buffer)
        self._using_alpaca = False

    def start(self):
        ok = self._alpaca.start()
        if not ok:
            self._yf.start()
        self._using_alpaca = ok

    def stop(self):
        self._alpaca.stop()
        self._yf.stop()
        logger.info("LiveFeed stopped.")

    def warmup_from_history(self):
        """Seed the buffer with recent historical bars via yfinance."""
        logger.info(f"Warming up bar buffers ({WARM_UP_BARS} bars per symbol) ...")
        for sym in SYMBOLS:
            yf_sym = YFINANCE_SYMBOLS.get(sym, sym)
            try:
                raw = yf.download(
                    yf_sym,
                    period="5d",
                    interval="1m",
                    auto_adjust=True,
                    progress=False,
                    threads=False,
                )
                if raw.empty:
                    logger.warning(f"  {sym}: no warmup data")
                    continue

                if isinstance(raw.columns, pd.MultiIndex):
                    raw.columns = raw.columns.get_level_values(0)
                raw.columns = [c.lower() for c in raw.columns]
                raw.index   = pd.to_datetime(raw.index, utc=True)
                raw.sort_index(inplace=True)
                raw = raw.tail(WARM_UP_BARS)

                for ts, row in raw.iterrows():
                    b = {
                        "ts":     ts.to_pydatetime(),
                        "open":   float(row["open"]),
                        "high":   float(row["high"]),
                        "low":    float(row["low"]),
                        "close":  float(row["close"]),
                        "volume": float(row.get("volume", 0)),
                    }
                    self.buffer.push(sym, b)

                logger.info(f"  {sym}: {len(raw)} warmup bars loaded")
            except Exception as exc:
                logger.error(f"  {sym}: warmup failed: {exc}")
