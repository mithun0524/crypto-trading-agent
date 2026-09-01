"""
model/predict.py — Deterministic inference wrapper.

Loads the trained model pkl and exposes a single predict() function.
Determinism guarantee: same feature row → same output, always.
Model version is logged with every prediction for auditability.
"""
from __future__ import annotations

import pickle
from pathlib import Path
from functools import lru_cache

import numpy as np
import pandas as pd
from loguru import logger

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import MODELS_DIR, REGIMES


@lru_cache(maxsize=1)
def _load_model(model_path: str) -> dict:
    """Load and cache the model payload from disk. Cached per path."""
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Model not found at {path}. "
            "Run 'python -m agent.model.train' first."
        )
    with open(path, "rb") as f:
        payload = pickle.load(f)
    logger.info(
        f"Loaded model v{payload['version']} "
        f"(trained {payload['trained_at']}, val Sharpe {payload['val_sharpe']:.3f})"
    )
    return payload


def predict(
    features: pd.DataFrame | pd.Series,
    model_path: Path | None = None,
) -> tuple[str, str]:
    """
    Run deterministic regime prediction.

    Parameters
    ----------
    features   : single-row DataFrame or Series of feature values
    model_path : path to .pkl file (defaults to latest in MODELS_DIR)

    Returns
    -------
    (regime_label, model_version) — e.g. ("TREND_UP", "20240901_0930")
    """
    if model_path is None:
        model_path = MODELS_DIR / "regime_model_latest.pkl"

    payload = _load_model(str(model_path))
    model        = payload["model"]
    feature_cols = payload["feature_cols"]
    label_map    = payload["label_map"]
    rev_map      = {v: k for k, v in label_map.items()}
    version      = payload["version"]

    # Build feature vector — fill any missing columns with 0 (safe default)
    if isinstance(features, pd.Series):
        row = features.to_frame().T
    else:
        row = features.tail(1).copy()  # always use the most recent completed bar

    X = pd.DataFrame(0.0, index=[0], columns=feature_cols)
    for col in feature_cols:
        if col in row.columns:
            X.at[0, col] = float(row.iloc[0][col])

    # Deterministic argmax prediction (no sampling, no probability thresholding)
    pred_int = int(model.predict(X)[0])
    regime   = rev_map.get(pred_int, "FLAT")

    return regime, version


def predict_proba(
    features: pd.DataFrame | pd.Series,
    model_path: Path | None = None,
) -> dict[str, float]:
    """
    Return class probabilities (for monitoring / logging only, NOT for signal generation).
    Actual trading decisions always use predict() → argmax.
    """
    if model_path is None:
        model_path = MODELS_DIR / "regime_model_latest.pkl"

    payload = _load_model(str(model_path))
    model        = payload["model"]
    feature_cols = payload["feature_cols"]
    label_map    = payload["label_map"]
    rev_map      = {v: k for k, v in label_map.items()}

    if isinstance(features, pd.Series):
        row = features.to_frame().T
    else:
        row = features.tail(1).copy()

    X = pd.DataFrame(0.0, index=[0], columns=feature_cols)
    for col in feature_cols:
        if col in row.columns:
            X.at[0, col] = float(row.iloc[0][col])

    proba = model.predict_proba(X)[0]
    return {rev_map.get(i, "FLAT"): float(p) for i, p in enumerate(proba)}


def reload_model(model_path: Path | None = None):
    """Force reload the model from disk (call after a new model is deployed)."""
    _load_model.cache_clear()
    if model_path:
        _load_model(str(model_path))
    else:
        _load_model(str(MODELS_DIR / "regime_model_latest.pkl"))
    logger.info("Model cache cleared and reloaded.")
