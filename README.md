# AlgoPaper — Deterministic Multi-Strategy Live Paper Trading Agent

A regime-aware, ML-driven paper trading agent that watches 9 US equities in **real-time** via Alpaca WebSocket, classifies market regimes with XGBoost, executes paper trades, and publishes live results to a public Next.js dashboard.

**Total monthly cost: $0**

---

## Watchlist

`SPY · QQQ · IWM · AAPL · NVDA · MSFT · AMZN · JPM · META`

---

## Quick Start

### Step 1 — Clone & set up Python environment

```bash
cd agent
pip install -e ".[dev]"
cp ../.env.example ../.env
# Fill in .env with your Alpaca and Supabase keys (see below)
```

### Step 2 — Train the model (first time)

```bash
cd agent
python -m model.train --interval 1h
# Downloads 2 years of 1h bars, trains XGBoost, saves to agent/models/
```

### Step 3 — Run the backtest

```bash
python -m backtest.engine --interval 1h
# Output: backtest_results/equity_curve.csv + trades.csv
```

### Step 4 — Run live (locally, during US market hours)

```bash
python agent/main.py
# Starts at 9:25 AM ET, signals live at 9:30 AM ET, closes all at 3:58 PM ET
```

---

## You Need to Do (4 manual steps)

### 1. Alpaca API keys (free)
1. Go to [alpaca.markets](https://alpaca.markets) → Sign up (free)
2. Dashboard → Paper Trading → API Keys → Generate
3. Add to `.env`:
   ```
   ALPACA_API_KEY=your_key
   ALPACA_API_SECRET=your_secret
   ```

### 2. Supabase project (free)
1. Go to [supabase.com](https://supabase.com) → New project (free tier)
2. SQL Editor → New query → paste contents of `supabase/migrations/001_init.sql` → Run
3. Settings → API → copy Project URL and anon key
4. Add to `.env`:
   ```
   SUPABASE_URL=https://xxx.supabase.co
   SUPABASE_KEY=your_anon_key
   ```
5. Dashboard → Database → Replication → Enable Realtime on `live_quotes` and `equity_curve`

### 3. Deploy agent to Fly.io (free)
```bash
# Install flyctl: https://fly.io/docs/hands-on/install-flyctl/
flyctl auth login
flyctl launch --name algopaper-agent --no-deploy   # uses fly.toml
flyctl secrets set ALPACA_API_KEY=xxx ALPACA_API_SECRET=xxx SUPABASE_URL=xxx SUPABASE_KEY=xxx
flyctl deploy
```

### 4. Deploy dashboard to Vercel (free)
1. Push this repo to GitHub
2. Go to [vercel.com](https://vercel.com) → New Project → Import from GitHub → select `dashboard/` as root directory
3. Add environment variables:
   - `NEXT_PUBLIC_SUPABASE_URL` = your Supabase URL
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` = your Supabase anon key
4. Deploy → done

---

## GitHub Actions — Secrets Required
Go to repo Settings → Secrets and variables → Actions → New repository secret:

| Secret | Value |
|---|---|
| `ALPACA_API_KEY` | Alpaca API key |
| `ALPACA_API_SECRET` | Alpaca API secret |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase anon key |
| `FLY_API_TOKEN` | `flyctl tokens create deploy` |

---

## Architecture

```
Alpaca WebSocket (1-min bars, 9 symbols)
    ↓ on each bar close (≤5s latency)
Rolling 200-bar buffer
    ↓
Feature engineering (28 features: RSI, ATR, EMA, Bollinger, Donchian, VIX, time-of-day)
    ↓
XGBoost regime classifier (TREND_UP / TREND_DOWN / RANGE / BREAKOUT / FLAT)
    ↓
Strategy router → EMA crossover / RSI+Bollinger / Donchian breakout
    ↓
Paper broker (ATR sizing, next-bar fill, circuit breaker)
    ↓
Supabase Postgres + Realtime
    ↓
Next.js dashboard (Vercel) — live Market Watch, equity curve, positions, trade log
```

---

## Repo Structure

```
agent/          Python trading agent
  config.py     All symbols, risk params, env vars
  data/         Feed (Alpaca WS + yfinance fallback) + history download + FRED
  features/     Feature engineering (28 indicators)
  model/        XGBoost training, inference, weekly retrain
  strategy/     EMA trend / RSI+BB mean-reversion / Donchian breakout
  broker/       Paper broker with ATR sizing + circuit breaker
  backtest/     Offline backtest engine
  db/           Supabase client
  main.py       Live agent entry point

dashboard/      Next.js 14 dashboard
  app/          Pages: overview, positions, trades, model
  components/   MarketWatch, EquityCurve, RegimeGrid, PositionsTable, TradeLog
  lib/          Supabase client + Realtime hooks

supabase/
  migrations/   001_init.sql — all tables + Realtime setup

.github/
  workflows/    retrain.yml — weekly Sunday retrain cron

Dockerfile      Agent Docker image
fly.toml        Fly.io deployment config
```

---

## Disclaimer

Paper trading only. Not investment advice. Do not use for real money without extensive additional validation.
