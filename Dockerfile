# â”€â”€ Builder stage â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build tools for any compiled dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY agent/pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir hatchling && \
    pip install --no-cache-dir -e ".[dev]" || true

# Install heavy ML packages one by one to avoid OOM on free-tier builders
RUN pip install --no-cache-dir "numpy>=1.26.0" "pandas>=2.1.0"
RUN pip install --no-cache-dir "scikit-learn>=1.3.0" "joblib>=1.3.0"
RUN pip install --no-cache-dir "xgboost>=2.0.0"
RUN pip install --no-cache-dir "lightgbm>=4.1.0"

# Install remaining dependencies
RUN pip install --no-cache-dir \
    "alpaca-py>=0.20.0" \
    "yfinance>=0.2.40" \
    "pandas-datareader>=0.10.0" \
    "requests>=2.31.0" \
    "pandas-ta" \
    "supabase>=2.3.0" \
    "python-dotenv>=1.0.0" \
    "pytz>=2024.1" \
    "schedule>=1.2.0" \
    "loguru>=0.7.2" \
    "httpx>=0.26.0" \`n    "websocket-client>=1.8.0"

# â”€â”€ Runtime stage â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy agent source + trained model
COPY agent/ ./agent/

# Timezone data (needed for America/New_York)
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && \
    rm -rf /var/lib/apt/lists/*

ENV TZ=UTC
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Health check â€” process is alive if main.py is running
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD pgrep -f "python agent/main.py" || exit 1

CMD ["python", "agent/main.py"]


