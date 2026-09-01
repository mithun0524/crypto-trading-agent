"""
data/history.py -- Bulk historical crypto bar download via yfinance.
Used ONLY for offline model training and backtesting.
"""
from __future__ import annotations

import datetime as dt
import time
from pathlib import Path

import pandas as pd
import yfinance as yf
from loguru import logger

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import SYMBOLS, YFINANCE_SYMBOLS, HISTORY_YEARS, DATA_DIR


def download_bars(
    symbols: list[str] | None = None,
    interval: str = "1h",
    years: int = HISTORY_YEARS,
    force: bool = False,
) -> dict[str, pd.DataFrame]:
    """
    Download historical OHLCV bars for all crypto symbols.
    Uses YFINANCE_SYMBOLS map to convert Alpaca format -> yfinance format.
    """
    if symbols is None:
        symbols = SYMBOLS

    # yfinance max: 1h = 730 days, 1m = 7 days
    if interval == "1m":
        start = (dt.datetime.now() - dt.timedelta(days=7)).strftime("%Y-%m-%d")
    elif interval == "1h":
        start = (dt.datetime.now() - dt.timedelta(days=729)).strftime("%Y-%m-%d")
    else:
        start = (dt.datetime.now() - dt.timedelta(days=years * 365)).strftime("%Y-%m-%d")

    end = dt.datetime.now().strftime("%Y-%m-%d")
    all_bars: dict[str, pd.DataFrame] = {}

    for sym in symbols:
        yf_sym = YFINANCE_SYMBOLS.get(sym, sym.replace("/", "-"))
        cache_path = DATA_DIR / f"{sym.replace('/', '_')}_{interval}.parquet"

        if cache_path.exists() and not force:
            logger.info(f"Loading cached bars: {cache_path.name}")
            df = pd.read_parquet(cache_path)
            all_bars[sym] = df
            continue

        logger.info(f"Downloading {yf_sym} {interval} bars ({start} -> {end}) ...")
        try:
            raw = yf.download(
                yf_sym,
                start=start,
                end=end,
                interval=interval,
                auto_adjust=True,
                progress=False,
                threads=False,
            )
            if raw.empty:
                logger.warning(f"No data for {yf_sym}")
                continue

            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = raw.columns.get_level_values(0)

            df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
            df.columns = ["open", "high", "low", "close", "volume"]
            df.index = pd.to_datetime(df.index, utc=True)
            df.index.name = "ts"
            df.dropna(subset=["close"], inplace=True)

            df.to_parquet(cache_path)
            all_bars[sym] = df
            logger.success(f"  {sym}: {len(df)} bars ({df.index[0].date()} -> {df.index[-1].date()})")
            time.sleep(0.5)

        except Exception as exc:
            logger.error(f"Failed to download {sym}: {exc}")

    return all_bars
