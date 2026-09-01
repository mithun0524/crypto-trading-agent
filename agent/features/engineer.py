"""
features/engineer.py -- CryptoPaper feature engineering.

Research-backed crypto feature stack (2025 best practices):
  - MACD + RSI + StochRSI + ADX  (momentum holy trinity)
  - Bollinger Band squeeze        (breakout signal)
  - OBV                           (volume confirms moves)
  - ATR-based volatility          (dynamic risk sizing)
  - Fear & Greed Index            (contrarian sentiment edge)
  - 24/7 time features            (crypto-specific session flags)
  - Multi-timeframe returns       (1h, 4h, 12h, 24h)

No US equity features. No FRED/VIX. Pure crypto.
"""
from __future__ import annotations
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pandas_ta as ta

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import RSI_PERIOD, ATR_PERIOD, BB_PERIOD, DONCHIAN_N, VOLUME_MA_N, EMA_FAST, EMA_SLOW

warnings.filterwarnings("ignore")


def compute_features(df: pd.DataFrame, fng_series: dict | None = None) -> pd.DataFrame:
    """
    Compute all crypto features.

    Parameters
    ----------
    df         : OHLCV DataFrame with UTC DatetimeIndex
    fng_series : optional dict of {date -> fng_value} from sentiment.py
    """
    df = df.copy()
    c  = df["close"]
    h, l, v = df["high"], df["low"], df["volume"]

    # -- Multi-timeframe returns (1h, 4h, 12h, 24h, 7d) ----------------------
    for n in [1, 4, 12, 24, 168]:
        df[f"ret_{n}b"] = c.pct_change(n)
    df["log_ret_1b"] = np.log(c / c.shift(1))

    # -- Volatility (24/7 annualised: 365*24 periods/year) --------------------
    df["realvol_24h"] = df["log_ret_1b"].rolling(24).std()  * np.sqrt(365 * 24)
    df["realvol_7d"]  = df["log_ret_1b"].rolling(168).std() * np.sqrt(365 * 24)
    df["vol_regime"]  = df["realvol_24h"] / (df["realvol_7d"] + 1e-9)  # 1=normal, >1=spike

    # -- RSI -------------------------------------------------------------------
    df["rsi"]       = ta.rsi(c, length=RSI_PERIOD)
    df["rsi_slope"] = df["rsi"].diff(3)
    # RSI zones (binary flags -- cleaner for tree models)
    df["rsi_oversold"]   = (df["rsi"] < 35).astype(int)
    df["rsi_overbought"] = (df["rsi"] > 70).astype(int)

    # -- StochRSI (great at picking exact turning points in crypto) -----------
    stoch = ta.stochrsi(c, length=14, rsi_length=14, k=3, d=3)
    if stoch is not None and not stoch.empty:
        k_cols = [x for x in stoch.columns if "STOCHRSIk" in x]
        d_cols = [x for x in stoch.columns if "STOCHRSId" in x]
        if k_cols and d_cols:
            df["stochrsi_k"]    = stoch[k_cols[0]]
            df["stochrsi_d"]    = stoch[d_cols[0]]
            df["stochrsi_bull"] = (df["stochrsi_k"] > df["stochrsi_d"]).astype(int)

    # -- ATR -------------------------------------------------------------------
    df["atr"]     = ta.atr(h, l, c, length=ATR_PERIOD)
    df["atr_pct"] = df["atr"] / c

    # -- Bollinger Bands + Squeeze -------------------------------------------
    bb = ta.bbands(c, length=BB_PERIOD, std=2.0)
    if bb is not None and not bb.empty:
        bbu = [x for x in bb.columns if x.startswith("BBU")]
        bbl = [x for x in bb.columns if x.startswith("BBL")]
        bbm = [x for x in bb.columns if x.startswith("BBM")]
        if bbu and bbl and bbm:
            df["bb_upper"] = bb[bbu[0]]
            df["bb_lower"] = bb[bbl[0]]
            df["bb_mid"]   = bb[bbm[0]]
            df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / (df["bb_mid"] + 1e-9)
            df["bb_pos"]   = (c - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"] + 1e-9)
            # Squeeze: BB width below its own 50-bar average = coiled spring
            bb_avg         = df["bb_width"].rolling(50).mean()
            df["bb_squeeze"] = (df["bb_width"] < bb_avg * 0.85).astype(int)
            df["bb_expand"]  = (df["bb_width"] > bb_avg * 1.30).astype(int)  # expanding = breakout confirmed

    # -- MACD (12/26/9 -- crypto standard) ------------------------------------
    macd = ta.macd(c, fast=EMA_FAST, slow=EMA_SLOW, signal=9)
    if macd is not None and not macd.empty:
        mc = [x for x in macd.columns if "MACD_" in x and "MACDs" not in x and "MACDh" not in x]
        ms = [x for x in macd.columns if "MACDs" in x]
        mh = [x for x in macd.columns if "MACDh" in x]
        if mc and ms and mh:
            df["macd"]      = macd[mc[0]]
            df["macd_sig"]  = macd[ms[0]]
            df["macd_hist"] = macd[mh[0]]
            df["macd_bull"] = (df["macd"] > df["macd_sig"]).astype(int)
            df["macd_hist_rising"] = (df["macd_hist"] > df["macd_hist"].shift(1)).astype(int)

    # -- EMA (12/26) crossover ------------------------------------------------
    df["ema_fast"]       = ta.ema(c, length=EMA_FAST)
    df["ema_slow"]       = ta.ema(c, length=EMA_SLOW)
    df["ema_cross"]      = df["ema_fast"] - df["ema_slow"]
    df["ema_cross_pct"]  = df["ema_cross"] / c
    df["ema_bull"]       = (df["ema_cross"] > 0).astype(int)

    # -- ADX (trend strength -- key for filtering noise) ----------------------
    adx_df = ta.adx(h, l, c, length=14)
    if adx_df is not None and not adx_df.empty:
        ac = [x for x in adx_df.columns if x.startswith("ADX")]
        dp = [x for x in adx_df.columns if x.startswith("DMP")]
        dn = [x for x in adx_df.columns if x.startswith("DMN")]
        if ac and dp and dn:
            df["adx"]        = adx_df[ac[0]]
            df["adx_strong"] = (df["adx"] > 25).astype(int)   # trending
            df["adx_weak"]   = (df["adx"] < 18).astype(int)   # choppy / ranging
            df["dmp"]        = adx_df[dp[0]]
            df["dmn"]        = adx_df[dn[0]]
            df["di_bull"]    = (df["dmp"] > df["dmn"]).astype(int)

    # -- OBV (On-Balance Volume -- volume confirms direction) -----------------
    df["obv"]       = ta.obv(c, v)
    df["obv_ema"]   = ta.ema(df["obv"], length=20)
    df["obv_bull"]  = (df["obv"] > df["obv_ema"]).astype(int)  # OBV above EMA = bullish

    # -- Donchian Channel (48h = 2-day breakout) ------------------------------
    dc = ta.donchian(h, l, lower_length=DONCHIAN_N, upper_length=DONCHIAN_N)
    if dc is not None and not dc.empty:
        dcu = [x for x in dc.columns if x.startswith("DCU")]
        dcl = [x for x in dc.columns if x.startswith("DCL")]
        if dcu and dcl:
            df["dc_upper"]    = dc[dcu[0]]
            df["dc_lower"]    = dc[dcl[0]]
            df["dc_pos"]      = (c - df["dc_lower"]) / (df["dc_upper"] - df["dc_lower"] + 1e-9)
            df["near_dc_high"] = (df["dc_pos"] > 0.85).astype(int)
            df["near_dc_low"]  = (df["dc_pos"] < 0.15).astype(int)

    # -- Volume features ------------------------------------------------------
    df["vol_ma_24h"] = v.rolling(VOLUME_MA_N).mean()
    df["vol_ratio"]  = v / (df["vol_ma_24h"] + 1)
    df["vol_surge"]  = (df["vol_ratio"] > 2.5).astype(int)
    df["vol_ret"]    = v.pct_change(1)

    # -- VWAP distance (24h rolling) ------------------------------------------
    typical = (h + l + c) / 3
    df["vwap_24h"] = (typical * v).rolling(24).sum() / (v.rolling(24).sum() + 1)
    df["vwap_dist"] = (c - df["vwap_24h"]) / c

    # -- SMA distances (trend context) ----------------------------------------
    for period in [20, 50, 200]:
        sma = c.rolling(period).mean()
        df[f"dist_sma{period}"] = (c - sma) / sma

    # -- Fear & Greed Index (sentiment edge) ----------------------------------
    if df.index.tz is None:
        idx_utc = df.index.tz_localize("UTC")
    else:
        idx_utc = df.index.tz_convert("UTC")

    if fng_series:
        df["fng_value"]    = idx_utc.date
        df["fng_value"]    = df["fng_value"].map(fng_series).fillna(50).astype(float)
        df["fng_fear"]     = (df["fng_value"] < 30).astype(int)   # extreme fear = buy signal
        df["fng_greed"]    = (df["fng_value"] > 70).astype(int)   # extreme greed = caution
    else:
        df["fng_value"] = 50.0
        df["fng_fear"]  = 0
        df["fng_greed"] = 0

    # -- Crypto time-of-day (24/7, UTC-based) ---------------------------------
    hour = idx_utc.hour
    dow  = idx_utc.dayofweek
    df["hour_utc"]   = hour
    df["is_weekend"] = (dow >= 5).astype(int)
    df["is_asia"]    = ((hour >= 0)  & (hour < 8)).astype(int)
    df["is_europe"]  = ((hour >= 8)  & (hour < 14)).astype(int)
    df["is_us"]      = ((hour >= 13) & (hour < 22)).astype(int)
    df["is_dead"]    = ((hour >= 22) | (hour < 2)).astype(int)

    # -- Drop NaN rows --------------------------------------------------------
    feature_cols = [col for col in df.columns if col not in ("open","high","low","close","volume")]
    df.dropna(subset=feature_cols, inplace=True)
    return df


def feature_columns() -> list[str]:
    """Full ordered feature list for XGBoost."""
    return [
        # Returns
        "ret_1b","ret_4b","ret_12b","ret_24b","ret_168b","log_ret_1b",
        # Volatility
        "realvol_24h","realvol_7d","vol_regime",
        # RSI
        "rsi","rsi_slope","rsi_oversold","rsi_overbought",
        # StochRSI
        "stochrsi_k","stochrsi_d","stochrsi_bull",
        # ATR
        "atr_pct",
        # Bollinger Bands
        "bb_width","bb_pos","bb_squeeze","bb_expand",
        # MACD
        "macd_hist","macd_bull","macd_hist_rising",
        # EMA
        "ema_cross_pct","ema_bull",
        # ADX
        "adx","adx_strong","adx_weak","di_bull",
        # OBV
        "obv_bull",
        # Donchian
        "dc_pos","near_dc_high","near_dc_low",
        # Volume
        "vol_ratio","vol_surge","vol_ret","vwap_dist",
        # SMA
        "dist_sma20","dist_sma50","dist_sma200",
        # Sentiment (Fear & Greed)
        "fng_value","fng_fear","fng_greed",
        # Time
        "hour_utc","is_weekend","is_asia","is_europe","is_us","is_dead",
    ]
