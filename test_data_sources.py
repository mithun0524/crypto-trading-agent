import yfinance as yf
import pandas as pd
import requests

# Test yfinance
raw = yf.download("SPY", period="5d", interval="1h", progress=False, auto_adjust=True)
if isinstance(raw.columns, pd.MultiIndex):
    raw.columns = raw.columns.get_level_values(0)
last_close = float(raw["Close"].iloc[-1])
print(f"yfinance SPY: {len(raw)} bars loaded, last close = ${last_close:.2f}")

# Test FRED
resp = requests.get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS", timeout=10)
last_line = resp.text.strip().split("\n")[-1]
date, vix = last_line.split(",")
print(f"FRED VIX = {vix.strip()} (as of {date.strip()})")

print("All free-tier data sources OK")
