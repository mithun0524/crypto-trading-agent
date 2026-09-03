"""
data/feed.py -- Crypto Live Feed Manager.

Crypto is 24/7 -- no market hours gate needed.
Connects directly to Binance's free public WebSocket for true real-time data,
without needing API keys!
"""
from __future__ import annotations

import collections
import json
import threading
import time
from typing import Callable

import pandas as pd
import yfinance as yf
import websocket
from loguru import logger

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    SYMBOLS, YFINANCE_SYMBOLS, WARM_UP_BARS
)

BarCallback = Callable[[str, dict], None]

# Map Alpaca pairs to Binance websocket stream names
BINANCE_SYMBOLS = {
    "BTC/USD": "btcusdt",
    "ETH/USD": "ethusdt",
    "SOL/USD": "solusdt",
    "DOGE/USD": "dogeusdt",
}
# Reverse map to convert binance symbol back to Alpaca format
REV_BINANCE_SYMBOLS = {v: k for k, v in BINANCE_SYMBOLS.items()}


# -- Rolling bar buffer -------------------------------------------------------

class BarBuffer:
    """Fixed-length deque of bars per symbol."""

    def __init__(self, maxlen: int = 15_000):
        """Hold up to 15,000 1-min bars per symbol (~10 days) so we can resample to 200+ hourly bars."""
        self._data: dict[str, collections.deque] = {
            s: collections.deque(maxlen=maxlen) for s in SYMBOLS
        }

    def push(self, symbol: str, bar: dict):
        if symbol not in self._data:
            self._data[symbol] = collections.deque(maxlen=15_000)
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


# -- Binance Free Crypto WebSocket --------------------------------------------

class BinanceFeed:
    """Connects to Binance public websocket for free, real-time 1m bars."""

    def __init__(self, on_bar: BarCallback, buffer: BarBuffer, on_tick=None):
        self.on_bar = on_bar
        self.buffer = buffer
        self.on_tick = on_tick
        self._last_tick_time = collections.defaultdict(float)
        self.ws = None
        self._running = False
        
        # Build stream URL for all symbols
        streams = [f"{s}@kline_1m" for s in BINANCE_SYMBOLS.values()]
        self.ws_url = f"wss://stream.binance.us:9443/ws/{'/'.join(streams)}"

    def start(self):
        self._running = True
        self._thread = threading.Thread(
            target=self._run_ws,
            name="binance-crypto-ws",
            daemon=True,
        )
        self._thread.start()
        logger.success(f"Binance Public WebSocket starting for {len(SYMBOLS)} pairs")
        return True

    def stop(self):
        self._running = False
        if self.ws:
            self.ws.close()

    def _run_ws(self):
        def on_message(ws, message):
            data = json.loads(message)
            if "k" in data:
                kline = data["k"]
                # Only process closed bars (x: True means the 1m bar is complete)
                if kline.get("x"):
                    binance_sym = kline["s"].lower()
                    alpaca_sym = REV_BINANCE_SYMBOLS.get(binance_sym)
                    if not alpaca_sym:
                        return
                        

                    if self.on_tick:
                        now = time.time()
                        if now - self._last_tick_time[alpaca_sym] >= 1.0:
                            self._last_tick_time[alpaca_sym] = now
                            self.on_tick(alpaca_sym, float(kline["c"]), float(kline["v"]))

                    bar = {
                        # Convert ms timestamp to datetime
                        "ts": pd.to_datetime(kline["T"], unit="ms", utc=True).to_pydatetime(),
                        "open": float(kline["o"]),
                        "high": float(kline["h"]),
                        "low": float(kline["l"]),
                        "close": float(kline["c"]),
                        "volume": float(kline["v"]),
                    }
                    self.buffer.push(alpaca_sym, bar)
                    self.on_bar(alpaca_sym, bar)

        def on_error(ws, error):
            logger.error(f"Binance WS Error: {error}")

        def on_close(ws, close_status_code, close_msg):
            logger.warning("Binance WS Closed.")

        def on_open(ws):
            logger.info("Binance WS Connected!")

        while self._running:
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            self.ws.run_forever()
            
            if self._running:
                logger.info("Reconnecting Binance WS in 5s...")
                time.sleep(5)


# -- Unified LiveFeed ---------------------------------------------------------

class LiveFeed:
    """
    Unified live feed. Uses Binance Public WebSockets.
    """

    def __init__(self, on_bar: BarCallback, on_tick=None):
        self.buffer = BarBuffer()
        self._binance = BinanceFeed(on_bar, self.buffer, on_tick=on_tick)
        self._using_alpaca = False  # Not using Alpaca anymore!

    def start(self):
        self._binance.start()

    def stop(self):
        self._binance.stop()
        logger.info("LiveFeed stopped.")

    def warmup_from_history(self):
        """
        Seed the buffer with recent historical 1-hour bars via yfinance.
        We load 15 days of 1-hour data (~360 bars). 
        We need at least 200 bars for the 200-SMA in features.
        """
        logger.info(f"Warming up bar buffers (1-hour history, last 15d) ...")
        for sym in SYMBOLS:
            yf_sym = YFINANCE_SYMBOLS.get(sym, sym)
            try:
                raw = yf.download(
                    yf_sym,
                    period="15d",
                    interval="1h",
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
                raw.index = pd.to_datetime(raw.index, utc=True)
                raw.sort_index(inplace=True)

                for ts, row in raw.iterrows():
                    b = {
                        "ts": ts.to_pydatetime(),
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                        "volume": float(row.get("volume", 0)),
                    }
                    self.buffer.push(sym, b)

                logger.info(f"  {sym}: {len(raw)} warmup bars loaded")
            except Exception as exc:
                logger.error(f"  {sym}: warmup failed: {exc}")





