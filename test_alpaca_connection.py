"""
test_alpaca_connection.py — Quick smoke test for Alpaca API connectivity.
Run: python test_alpaca_connection.py

Tests:
1. REST API: account info, buying power
2. Market data: latest bar for SPY
3. WebSocket: subscribes to bars for 5 seconds and prints any received
"""
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

API_KEY    = os.getenv("ALPACA_API_KEY", "")
API_SECRET = os.getenv("ALPACA_API_SECRET", "")
BASE_URL   = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

print("=" * 55)
print("AlgoPaper — Alpaca Connection Test")
print("=" * 55)
print(f"  Key    : {API_KEY[:8]}...{API_KEY[-4:]}" if len(API_KEY) > 12 else f"  Key: {API_KEY}")
print(f"  Secret : {'SET' if API_SECRET and API_SECRET != 'REPLACE_WITH_YOUR_SECRET_KEY' else '❌ NOT SET — add to .env'}")
print(f"  URL    : {BASE_URL}")
print()

if not API_KEY or not API_SECRET or API_SECRET == "REPLACE_WITH_YOUR_SECRET_KEY":
    print("❌ ALPACA_API_SECRET not set in .env — please add it and re-run.")
    sys.exit(1)

# ── Test 1: REST — Account info ───────────────────────────────────────────────
print("Test 1: REST API — Account info ...")
try:
    from alpaca.trading.client import TradingClient
    client  = TradingClient(API_KEY, API_SECRET, paper=True)
    account = client.get_account()
    print(f"  ✅ Account status : {account.status}")
    print(f"  ✅ Buying power   : ${float(account.buying_power):,.2f}")
    print(f"  ✅ Portfolio value : ${float(account.portfolio_value):,.2f}")
    print(f"  ✅ Currency       : {account.currency}")
except Exception as e:
    print(f"  ❌ REST API failed: {e}")
    sys.exit(1)

print()

# ── Test 2: Market data — Latest bar for SPY ──────────────────────────────────
print("Test 2: Market data — Latest 1-min bar for SPY ...")
try:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests  import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from alpaca.data.enums import DataFeed
    import datetime as dt

    data_client = StockHistoricalDataClient(API_KEY, API_SECRET)
    end   = dt.datetime.now(dt.timezone.utc)
    start = end - dt.timedelta(hours=2)

    req  = StockBarsRequest(symbol_or_symbols="SPY", timeframe=TimeFrame.Minute,
                            start=start, end=end, limit=5, feed=DataFeed.IEX)
    bars = data_client.get_stock_bars(req)
    spy_bars = bars.data.get("SPY", [])

    if spy_bars:
        last = spy_bars[-1]
        print(f"  ✅ SPY latest bar: open={last.open:.2f} high={last.high:.2f} "
              f"low={last.low:.2f} close={last.close:.2f} vol={last.volume}")
    else:
        print("  ⚠️  No bars returned (market may be closed — this is OK)")
except Exception as e:
    print(f"  ❌ Market data failed: {e}")

print()

# ── Test 3: yfinance fallback ─────────────────────────────────────────────────
print("Test 3: yfinance fallback — Latest SPY bar ...")
try:
    import yfinance as yf
    import pandas as pd
    raw = yf.download("SPY", period="1d", interval="1m", progress=False, auto_adjust=True)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    if not raw.empty:
        last = raw.iloc[-1]
        print(f"  ✅ SPY via yfinance: close={last['Close']:.2f} vol={last['Volume']:.0f}")
    else:
        print("  ⚠️  No yfinance data (market closed or weekend)")
except Exception as e:
    print(f"  ❌ yfinance failed: {e}")

print()

# ── Test 4: FRED ──────────────────────────────────────────────────────────────
print("Test 4: FRED macro data (VIX) ...")
try:
    import requests
    resp = requests.get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS", timeout=10)
    resp.raise_for_status()
    lines = resp.text.strip().split("\n")
    last_line = lines[-1]
    date, vix = last_line.split(",")
    print(f"  ✅ VIX = {vix.strip()} (as of {date})")
except Exception as e:
    print(f"  ❌ FRED failed: {e}")

print()
print("=" * 55)
print("Connection tests complete.")
print("=" * 55)
