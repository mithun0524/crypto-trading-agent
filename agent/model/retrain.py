"""
model/retrain.py — Weekly retraining entry point (called by GitHub Actions).
Downloads fresh data, retrains the model, saves versioned .pkl.
"""
from __future__ import annotations

import sys
from pathlib import Path
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent))
from model.train import train
from config import SYMBOLS


def main():
    logger.info("=== AlgoPaper Weekly Retrain ===")
    model_path = train(symbols=SYMBOLS, interval="1h")
    logger.success(f"Retrain complete → {model_path}")


if __name__ == "__main__":
    main()
