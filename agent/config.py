"""
config.py -- CryptoPaper agent configuration.
Pure crypto. No US equity references anywhere.
"""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# -- Paths --------------------------------------------------------------------
ROOT_DIR   = Path(__file__).parent
MODELS_DIR = ROOT_DIR / "models"
DATA_DIR   = ROOT_DIR / "data_cache"
MODELS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# -- Crypto Universe ----------------------------------------------------------
# Alpaca Crypto WebSocket format
SYMBOLS: list[str] = [
    "BTC/USD",    # Bitcoin -- market leader / regime anchor
    "ETH/USD",    # Ethereum -- DeFi bellwether
    "SOL/USD",    # Solana -- high-beta altcoin
    "DOGE/USD",   # Dogecoin -- sentiment / retail proxy
]

# yfinance format for historical data download
YFINANCE_SYMBOLS: dict[str, str] = {
    "BTC/USD":  "BTC-USD",
    "ETH/USD":  "ETH-USD",
    "SOL/USD":  "SOL-USD",
    "DOGE/USD": "DOGE-USD",
}

# -- Paper trading parameters -------------------------------------------------
STARTING_CASH:        float = 100_000.0
RISK_PER_TRADE_PCT:   float = 0.02        # 2% per trade (crypto is volatile)
MAX_POSITION_PCT:     float = 0.25        # max 25% per coin
MAX_OPEN_POSITIONS:   int   = 4
DAILY_LOSS_LIMIT_PCT: float = 0.05        # halt if down 5%
SLIPPAGE_PCT:         float = 0.0005      # 0.05% per side
COMMISSION_PCT:       float = 0.0         # Alpaca Crypto is commission-free

# -- Feature parameters -------------------------------------------------------
BAR_TIMEFRAME:    str   = "1Min"
WARM_UP_BARS:     int   = 200
HISTORY_YEARS:    int   = 2               # yfinance 1h max = 730 days
LABEL_HORIZON:    int   = 12              # 12-bar (12h) forward return
TREND_RETURN_PCT: float = 0.01            # 1% threshold to label BULL/BEAR
VOL_THRESHOLD:    float = 0.40            # annualised vol threshold for ACCUMULATION

# -- Crypto regime classes (NO US equity regimes) -----------------------------
REGIMES = ["BULL_TREND", "BEAR_TREND", "ACCUMULATION", "PUMP", "DUMP", "FLAT"]

# -- Indicator periods (tuned for crypto 24/7 hourly bars) --------------------
EMA_FAST:    int = 12    # ~12h fast EMA
EMA_SLOW:    int = 26    # ~26h slow EMA (MACD-style)
RSI_PERIOD:  int = 14
ATR_PERIOD:  int = 14
BB_PERIOD:   int = 20
DONCHIAN_N:  int = 48    # 48h = 2-day Donchian channel
VOLUME_MA_N: int = 24    # 24h volume moving average

# -- Alpaca -----------------------------------------------------------------
ALPACA_API_KEY:    str = os.getenv("ALPACA_API_KEY", "")
ALPACA_API_SECRET: str = os.getenv("ALPACA_API_SECRET", "")
ALPACA_BASE_URL:   str = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

# -- Supabase ---------------------------------------------------------------
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

# -- Model ------------------------------------------------------------------
MODEL_VERSION: str = os.getenv("MODEL_VERSION", "v1")
MODEL_PATH:    Path = MODELS_DIR / "regime_model_latest.pkl"
