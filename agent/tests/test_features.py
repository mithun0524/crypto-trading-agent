"""
tests/test_features.py — Unit tests for feature engineering.
"""
import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from features.engineer import compute_features, feature_columns


def make_bars(n: int = 250, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic OHLCV bars with a DatetimeIndex."""
    rng   = np.random.default_rng(seed)
    close = 400.0 + np.cumsum(rng.normal(0, 1, n))
    high  = close + rng.uniform(0.5, 2.0, n)
    low   = close - rng.uniform(0.5, 2.0, n)
    open_ = close + rng.normal(0, 0.5, n)
    vol   = rng.integers(100_000, 1_000_000, n).astype(float)

    idx = pd.date_range(
        start="2024-01-02 09:31",
        periods=n,
        freq="1min",
        tz="UTC",
    )
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": vol},
        index=idx,
    )


# ── Basic shape / no-lookahead checks ────────────────────────────────────────

def test_compute_features_returns_dataframe():
    bars = make_bars(250)
    feat = compute_features(bars, vix_level=18.0)
    assert isinstance(feat, pd.DataFrame)
    assert len(feat) > 0


def test_no_future_leakage():
    """
    If we drop the last bar and recompute, the second-to-last row of features
    must be identical. This is the key no-lookahead assertion.
    """
    bars  = make_bars(250)
    feat_full = compute_features(bars, vix_level=18.0)
    feat_trim = compute_features(bars.iloc[:-1], vix_level=18.0)

    # The last row of feat_trim should equal the second-to-last row of feat_full
    common_cols = [c for c in feature_columns() if c in feat_full.columns and c in feat_trim.columns]
    last_trim   = feat_trim.iloc[-1][common_cols]
    second_last = feat_full.iloc[-2][common_cols]

    # Allow tiny float diff from rolling window alignment
    assert (last_trim - second_last).abs().max() < 1e-6


def test_all_feature_columns_present():
    bars = make_bars(250)
    feat = compute_features(bars, vix_level=18.0)
    for col in feature_columns():
        assert col in feat.columns, f"Missing feature column: {col}"


def test_no_nan_in_features_after_warmup():
    bars = make_bars(250)
    feat = compute_features(bars, vix_level=18.0)
    # After warmup rows are dropped, no NaN should remain in feature columns
    feat_cols = [c for c in feature_columns() if c in feat.columns]
    assert not feat[feat_cols].isnull().any().any(), "NaN found in feature columns"


# ── VIX features ──────────────────────────────────────────────────────────────

def test_vix_features_propagated():
    bars = make_bars(250)
    feat = compute_features(bars, vix_level=30.0, vix_roc=0.05)
    assert (feat["vix"] == 30.0).all()
    assert (feat["vix_roc"] == 0.05).all()
    assert (feat["vix_hi"] == 1).all()   # 30 > 25 threshold


def test_vix_low_flag():
    bars = make_bars(250)
    feat = compute_features(bars, vix_level=12.0)
    assert (feat["vix_hi"] == 0).all()


# ── Time-of-day features ──────────────────────────────────────────────────────

def test_open_spike_flag():
    bars = make_bars(250)
    feat = compute_features(bars, vix_level=18.0)
    # Our bars start at 9:31 ET — should have open_spike = 1 for first ~14 rows
    # (bars from 9:31 to 9:44)
    open_spike_rows = feat[feat["is_open_spike"] == 1]
    assert len(open_spike_rows) > 0


# ── Indicator sanity ─────────────────────────────────────────────────────────

def test_rsi_bounds():
    bars = make_bars(300)
    feat = compute_features(bars, vix_level=18.0)
    assert feat["rsi"].between(0, 100).all(), "RSI out of [0, 100] range"


def test_bb_pos_roughly_bounded():
    bars = make_bars(300)
    feat = compute_features(bars, vix_level=18.0)
    # bb_pos can exceed [0,1] slightly for extreme moves, but most should be within
    within = feat["bb_pos"].between(-0.5, 1.5)
    assert within.mean() > 0.95


def test_vol_ratio_positive():
    bars = make_bars(250)
    feat = compute_features(bars, vix_level=18.0)
    assert (feat["vol_ratio"] >= 0).all()


def test_feature_count():
    expected = len(feature_columns())
    assert expected == 28, f"Expected 28 features, got {expected}"
