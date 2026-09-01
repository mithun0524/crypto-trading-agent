"""
data/sentiment.py -- Crypto sentiment data fetcher.

Sources (all FREE, no API key required):
  1. Alternative.me Fear & Greed Index -- daily sentiment 0-100
     https://api.alternative.me/fng/?limit=730

No US FRED/VIX. Pure crypto sentiment.
"""
from __future__ import annotations

import datetime as dt
import time
from functools import lru_cache

import requests
from loguru import logger


# -- Fear & Greed Index -------------------------------------------------------

FNG_URL = "https://api.alternative.me/fng/"


def fetch_fear_greed_history(days: int = 730) -> list[dict]:
    """
    Fetch up to `days` days of crypto Fear & Greed Index history.
    Returns list of dicts: [{date, value, classification}, ...]
    """
    try:
        resp = requests.get(
            FNG_URL,
            params={"limit": days, "format": "json"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        result = []
        for item in data:
            result.append({
                "date":           dt.datetime.utcfromtimestamp(int(item["timestamp"])).date(),
                "fng_value":      int(item["value"]),
                "fng_class":      item["value_classification"],  # e.g. "Fear", "Greed"
            })
        logger.info(f"Fear & Greed: fetched {len(result)} days of history")
        return result
    except Exception as exc:
        logger.error(f"Fear & Greed fetch failed: {exc}")
        return []


def get_latest_fear_greed() -> dict:
    """Get today's Fear & Greed value. Returns dict with fng_value (0-100)."""
    try:
        resp = requests.get(FNG_URL, params={"limit": 1}, timeout=8)
        resp.raise_for_status()
        data = resp.json().get("data", [{}])[0]
        val  = int(data.get("value", 50))
        cls  = data.get("value_classification", "Neutral")
        logger.info(f"Fear & Greed Index: {val} ({cls})")
        return {"fng_value": val, "fng_class": cls}
    except Exception as exc:
        logger.warning(f"Fear & Greed unavailable, using neutral (50): {exc}")
        return {"fng_value": 50, "fng_class": "Neutral"}


def build_fng_series(bars_index) -> dict:
    """
    Build a date -> fng_value lookup dict for aligning with hourly bars.
    """
    history = fetch_fear_greed_history(days=730)
    if not history:
        return {}
    return {row["date"]: row["fng_value"] for row in history}
