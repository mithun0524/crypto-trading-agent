"""
main.py -- CryptoPaper live trading agent entry point.

24/7 continuous loop (crypto never sleeps):
  Alpaca Crypto WebSocket -> rolling buffer -> features -> model -> router -> broker -> Supabase
"""
from __future__ import annotations

import datetime as dt
import signal
import sys
import threading
import time
import os
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    SYMBOLS, WARM_UP_BARS,
    SUPABASE_URL, SUPABASE_KEY,
)
from data.feed import LiveFeed
from features.engineer import compute_features
from model.predict import predict
from strategy.router import route
from broker.paper import PaperBroker
from db.supabase_client import (
    upsert_bar, upsert_signal, insert_trade, upsert_equity, upsert_live_quote,
)


class TradingAgent:
    """Main live 24/7 crypto trading agent."""

    def __init__(self):
        self.broker = PaperBroker()
        self.feed   = LiveFeed(on_bar=self._on_bar)
        self._shutdown = False
        self._lock     = threading.Lock()
        self._started  = False

    def start(self):
        logger.info("=" * 60)
        logger.info("🚀 CryptoPaper Live Trading Agent Starting")
        logger.info("=" * 60)

        # Warmup bar buffer from recent history
        self.feed.warmup_from_history()

        # Start live crypto feed
        self.feed.start()

        # Reset broker
        self.broker.reset_day({s: 0.0 for s in SYMBOLS})

        logger.success("Agent ready. Trading 24/7...")
        self._started = True

    def _on_bar(self, symbol: str, bar: dict):
        """Called on every incoming bar for every subscribed symbol."""
        with self._lock:
            ts = bar["ts"]
            if isinstance(ts, str):
                ts = dt.datetime.fromisoformat(ts)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=dt.timezone.utc)

            # Persist bar
            if SUPABASE_URL:
                upsert_bar(symbol, bar)

            close = float(bar["close"])

            # Fill pending orders
            filled = self.broker.fill_pending_orders(
                {symbol: float(bar["open"])}, ts, {symbol: close}
            )
            for trade in filled:
                if trade and SUPABASE_URL:
                    insert_trade(trade)

            # Signal generation (always enabled - crypto is 24/7)
            regime = "FLAT"
            signal_result = {"action": "HOLD", "strategy": "none", "reason": ""}

            if self.feed.buffer.ready(symbol, WARM_UP_BARS):
                bars_df = self.feed.buffer.to_dataframe(symbol)
                try:
                    feat_df = compute_features(bars_df)
                    if not feat_df.empty:
                        regime, model_ver = predict(feat_df)
                        open_pos = symbol in self.broker.positions
                        signal_result = route(regime, symbol, feat_df, open_position=open_pos)

                        curr_bar_dict = {
                            "close": close,
                            "open":  float(bar["open"]),
                            "atr":   float(feat_df.iloc[-1].get("atr", 0.0))
                                     if "atr" in feat_df.columns else 0.0,
                        }
                        order = self.broker.place_order(
                            signal_result, curr_bar_dict, {symbol: close}, model_ver
                        )

                        if SUPABASE_URL:
                            upsert_signal(
                                symbol, ts, regime,
                                signal_result["strategy"],
                                signal_result["action"],
                                signal_result.get("reason", ""),
                                model_ver,
                            )
                except Exception as exc:
                    logger.error(f"Signal generation error [{symbol}]: {exc}")

            # Persist live quote + equity snapshot
            if SUPABASE_URL:
                upsert_live_quote(symbol, close, 0.0, int(bar.get("volume", 0)), regime)
                snap = self.broker.snapshot({symbol: close})
                upsert_equity(ts, snap)

            logger.debug(
                f"  {symbol:<10} ${close:<12.4f} "
                f"regime={regime:<12} action={signal_result['action']}"
            )

    def stop(self):
        self._shutdown = True
        self.feed.stop()
        stats = self.broker.stats()
        logger.info(f"Final stats: {stats}")
        logger.info("Agent stopped.")


# -- Health-check HTTP server -------------------------------------------------

def _start_dummy_server(port: int):
    """Starts a basic HTTP server so Render health checks pass."""
    import http.server
    import socketserver

    class HealthCheckHandler(http.server.BaseHTTPRequestHandler):
        def _send_headers(self):
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.send_header("Content-Length", "2")
            self.send_header("Connection", "close")
            self.end_headers()

        def do_GET(self):
            self._send_headers()
            self.wfile.write(b"OK")

        def do_HEAD(self):
            self._send_headers()

        def log_message(self, format, *args):
            pass  # suppress noisy access logs

    httpd = socketserver.TCPServer(("0.0.0.0", port), HealthCheckHandler)
    logger.info(f"Started health-check server on port {port}")
    threading.Thread(target=httpd.serve_forever, daemon=True).start()


# -- Entry point --------------------------------------------------------------

def main():
    port = os.getenv("PORT")
    if port:
        _start_dummy_server(int(port))

    agent = TradingAgent()

    def _shutdown(signum, frame):
        logger.info("Shutdown signal received ...")
        agent.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # Start agent once
    agent.start()

    # Keep the process alive (24/7 - no market hours gate)
    while not agent._shutdown:
        time.sleep(10)


if __name__ == "__main__":
    main()
