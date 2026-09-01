# AlgoPaper — Deterministic Multi-Strategy Live Trading Agent

**One-line pitch:** A regime-aware, ML-driven trading agent that watches a curated list of stocks and indices in **real-time**, picks a deterministic strategy based on what the market is doing, executes paper trades the moment a signal fires, and shows live results on a public dashboard — for $0/month.

"Deterministic" means: the model is **trained once, offline**, and at inference time always produces the *same* output for the *same* input — no sampling, no LLM token costs, no surprises. It's a real trained classifier, not hand-tuned if/else rules.

---

## 1. Goals

- Watch a **curated 9-symbol watchlist** (see §4) in **real-time** — streaming 1-minute bars via WebSocket, not delayed polling — so no trade opportunity is missed.
- Trade paper money (starting balance: $100,000) against live price feeds.
- Use a trained ML model to classify market **regime** (trend / range / breakout / flat) per symbol per bar and route to the matching strategy.
- Zero recurring cost: no paid data feeds, no paid compute, no LLM API calls in the trading loop.
- Publicly viewable live dashboard: live market watch panel (prices + % change for all 9 symbols), equity curve, open positions, trade blotter, per-strategy win rate.
- Fully reproducible backtests: same model + same historical data + same date range = identical trade log every time.

## 2. Non-goals (v1)

- No real money, no broker integration (Alpaca/IBKR can be added later behind a feature flag).
- No shorting or options — long/flat only.
- No HFT or order-book strategies — signal granularity is 1-minute bars from the live feed.
- No continuous retraining in production — model retrains on a schedule (weekly), not per-trade.

## 3. Users

Just you (Mithun) — a solo-builder project to (a) learn quant/ML trading mechanics, (b) have a live public demo piece for your portfolio.

---

## 4. Watchlist (Curated, Tradeable Symbols)

A tight, high-liquidity watchlist you can realistically monitor, generate trade signals for, and back-test without data gaps. Selection criteria: high average daily volume, free data availability, good regime diversity.

### 4.1 — Index ETFs (regime anchors + directly tradeable)

| Symbol | Name | Why |
|---|---|---|
| **SPY** | S&P 500 ETF (SPDR) | Market benchmark; regime anchor; always tradeable |
| **QQQ** | Nasdaq-100 ETF (Invesco) | Tech-heavy; diverges from SPY in rotation regimes |
| **IWM** | Russell 2000 ETF (iShares) | Small-cap risk-on/off signal; mean-reversion prone |

### 4.2 — Individual Stocks (alpha + strategy diversity)

| Symbol | Name | Sector | Why |
|---|---|---|---|
| **AAPL** | Apple | Tech | Mega-cap, tight spreads, excellent data quality |
| **NVDA** | NVIDIA | Semiconductors | High-beta, breakout-prone — ideal for breakout strategy |
| **MSFT** | Microsoft | Tech | Steady trend characteristics — ideal for trend strategy |
| **AMZN** | Amazon | Consumer/Cloud | Range-bound phases alternate with breakouts |
| **JPM** | JPMorgan Chase | Financials | Sector diversification; mean-reversion prone |
| **META** | Meta Platforms | Tech/Social | High volatility regimes, strong trend phases |

### 4.3 — Regime Input (read-only, not traded)

| Symbol | Name | Role |
|---|---|---|
| **^VIX** | CBOE Volatility Index | Live regime feature — polled every minute; not traded |

### 4.4 — Active Trading Universe

```
SPY, QQQ, IWM, AAPL, NVDA, MSFT, AMZN, JPM, META
```

9 symbols — small enough for a free data feed and a single process, large enough for diversification and per-strategy routing.

---

## 5. System Architecture

The architecture is **event-driven**, not cron-driven. A persistent agent process subscribes to a WebSocket feed and reacts to every incoming 1-minute bar. No missed bars, no polling lag.

```
┌──────────────────────────┐   WebSocket (1-min bars)   ┌────────────────────────────────┐
│  Alpaca Markets           │ ─────────────────────────▶ │  Trading Agent Process          │
│  Free Data Stream         │  all 9 symbols             │  (Python, persistent,           │
│  (free account, no        │  + ^VIX poll every 60s     │   running during market hours)  │
│   trading required)       │                            │                                 │
└──────────────────────────┘                            │  on each bar close:             │
           │                                            │  → append to rolling buffer     │
           │ fallback if WS drops                       │  → compute features             │
           ▼                                            │  → model.predict() (regime)     │
┌──────────────────────────┐                            │  → strategy router              │
│  yfinance 60-sec polling  │                            │  → paper broker execute         │
│  (backup data source)     │                            │  → write to Supabase            │
└──────────────────────────┘                            └───────────┬────────────────────┘
                                                                    │ writes (upsert)
                                                                    ▼
                                                       ┌──────────────────────────┐
                                                       │  Supabase Postgres        │
                                                       │  + Realtime enabled       │
                                                       └──────────┬───────────────┘
                                                                  │ Realtime WS subscription
                                                                  ▼
                                                       ┌──────────────────────────┐
                                                       │  Next.js Dashboard        │
                                                       │  on Vercel (free)         │
                                                       │  • Market Watch (live)    │
                                                       │  • Equity curve           │
                                                       │  • Positions & trade log  │
                                                       └──────────────────────────┘
```

### Process Hosting (Always-On During Market Hours)

The agent process must stay alive from 9:25 AM – 4:00 PM ET on trading days. GitHub Actions is **not** suitable for this (it can't hold a persistent WebSocket). Options:

| Option | Cost | Notes |
|---|---|---|
| **Local machine** | $0 | Simplest to start — run the Python process during market hours |
| **Fly.io free tier** | $0 | 3 shared-CPU VMs; scale to zero outside market hours via `fly scale count 0` |
| **Railway free tier** | $0 | Always-on container, 512 MB RAM — sufficient for 9 symbols |
| **Render free tier** | $0 | Background worker; add a keep-alive ping to prevent idle spin-down |

> **Recommended:** develop and test locally first, then deploy to **Fly.io** for unattended live paper trading.

GitHub Actions is retained **only** for the weekly model retraining cron — not for the live trading loop.

---

## 6. Data Layer

| Purpose | Source | Notes |
|---|---|---|
| **Live streaming bars (1-min)** | **Alpaca Markets free data stream** (`alpaca-py`) | Free WebSocket for US equities + ETFs; no funded account required; ideal for 9 symbols |
| **Live streaming fallback** | `yfinance` 60-second polling | Not a true WebSocket but ~1-min latency; agent falls back automatically if Alpaca WS drops |
| **VIX live level** | `^VIX` via yfinance (polled every 60s) | Used as a live regime feature input; not a tradeable symbol in v1 |
| **Historical training data** | `yfinance` bulk download | 5+ years of 1-min bars per symbol; same library for training and live — no format mismatch |
| **Macro context (daily)** | FRED API (`VIXCLS`, `DGS10`) | Loaded once at market open each day; free, no key needed |

### Live Feed Design

```
Alpaca WebSocket
    ├── subscribe to bars: ["SPY", "QQQ", "IWM", "AAPL", "NVDA", "MSFT", "AMZN", "JPM", "META"]
    ├── event: bar { symbol, open, high, low, close, volume, timestamp }
    └── on bar received:
            buffer[symbol].append(bar)          # rolling 200-bar window per symbol
            if len(buffer[symbol]) >= MIN_BARS:
                trigger → features → regime → signal → paper broker → DB write
```

**Bar cadence:** 1-minute bars. Signals are evaluated once per bar close. Fast enough to catch intraday breakouts and trend entries; slow enough to avoid HFT-style noise.

**Signal latency target:** ≤ 5 seconds from bar close to DB write.

---

## 7. ML Model Spec

**Task:** Multi-class classification per 1-min bar → `{TREND_UP, TREND_DOWN, RANGE, BREAKOUT, FLAT}`, plus a binary direction signal for TREND/BREAKOUT regimes (long vs. flat).

**Labeling (offline, historical data only):**
- `TREND_UP/DOWN`: forward N-bar return exceeds ±X% AND realized volatility is below a rolling threshold.
- `RANGE`: price stays within a rolling Bollinger channel for the following N bars.
- `BREAKOUT`: a volatility squeeze (low rolling bandwidth) followed by a sharp expansion.
- `FLAT`: none of the above confidently.

**Features (past data only — no lookahead):**
- Returns over multiple lookbacks (1, 5, 10, 20 bars) on 1-min timeframe
- ADX, RSI(14), ATR(14), Bollinger bandwidth, Donchian channel position
- Volume relative to its own 20-bar moving average (volume surge = breakout signal)
- VIX live level and VIX 5-bar rate-of-change (regime context)
- Distance of price from 20/50/200-period moving averages (1-min and daily)
- **Time-of-day features:** is_open_spike (first 15 min), is_power_hour (last 60 min), is_lunch_lull (12–1 PM ET)

**Model:** `XGBoost` or `LightGBM`. Deterministic inference — same feature row always yields the same prediction — zero per-call cost once trained.

**Training loop (manual / Colab, not in production):**
1. Pull 5+ years of 1-min bars per symbol via yfinance or Alpaca historical API.
2. Build features + forward-looking labels on the 1-min timescale.
3. Time-based train/val/test split (never shuffle — this is a time series).
4. Train, evaluate (precision/recall per regime class, backtested Sharpe on held-out period).
5. Export as `.pkl` / `.onnx`, commit to repo (or Supabase Storage).
6. Retrain weekly via GitHub Actions; every prediction is logged with the model version for auditability.

**Determinism guarantee:** fix random seeds at training time; use `.predict()` (argmax) at inference, never `.predict_proba()` + sampling.

---

## 8. Strategy / Execution Layer

**Regime → Strategy Router:**

| Regime | Strategy | Logic |
|---|---|---|
| `TREND_UP` | EMA Crossover (long) | Enter long when fast EMA (9) crosses above slow EMA (21) on 1-min bars |
| `TREND_DOWN` | EMA Crossover (flat) | Close any long if fast EMA crosses below slow EMA |
| `RANGE` | RSI + Bollinger Mean-Reversion | Buy near lower band when RSI < 35; sell near upper band when RSI > 65 |
| `BREAKOUT` | Donchian Channel Breakout | Enter on N-bar high break with volume ≥ 1.5× 20-bar avg volume |
| `FLAT` | No new positions | Hold existing; tighten stops |

**Paper Broker:**
- Starting cash: $100,000 (configurable).
- Position sizing: fixed-fractional — risk 1–2% of equity per trade, sized off 1-min ATR.
- Orders fill at next bar's open (no same-bar lookahead).
- Slippage: 0.01% per side. Commission: $0.005/share (Alpaca-like model).
- One open position per symbol at a time in v1.

**Risk Limits:**
- Daily loss circuit-breaker: halt new trades if intraday drawdown exceeds 2% of starting equity.
- Max concurrent open positions: 4 out of 9 symbols.
- Max single-position size: 20% of total portfolio equity.

---

## 9. Live Loop Requirements

### Event-Driven, Not Cron-Driven

The loop reacts to each bar from the WebSocket, not a fixed timer. This means:
- No missed bars due to cron timing drift.
- Signal fires ≤ 5 seconds after bar close.
- If the feed drops, the agent pauses signal generation and logs an alert (optional Discord/Telegram webhook) — it never trades on stale data.

```python
# Core event handler — pseudocode
async def on_bar(bar: Bar):
    buffer[bar.symbol].append(bar)
    if len(buffer[bar.symbol]) < MIN_BARS:
        return  # not enough history yet

    features = compute_features(buffer[bar.symbol], vix_now)
    regime   = model.predict(features)          # deterministic
    signal   = strategy_router(regime, bar.symbol)
    trade    = paper_broker.execute(signal)
    await db.upsert(bar, signal, trade, equity_snapshot())
    await db.upsert_live_quote(bar.symbol, bar.close)  # triggers dashboard Realtime update
```

### Market Hours Handling

| Time (ET) | Action |
|---|---|
| 9:25 AM | Agent starts; loads last 200 bars from DB to warm up rolling buffer |
| 9:30 AM | WebSocket subscriptions go live; signal generation enabled |
| 3:58 PM | Close all open positions (avoid end-of-day illiquidity) |
| 4:00 PM | Agent disconnects gracefully; persists final equity snapshot |
| 4:01 PM | Process sleeps / Fly.io scales to zero until next trading day |

### Idempotency
- Bar writes are upserted on `(symbol, ts)` — re-processing the same bar never creates duplicate rows.
- Trade dedup on `(symbol, entry_ts)` — broker won't double-enter a position even if the signal fires twice.

---

## 10. Data Storage (Supabase / Postgres Tables)

```sql
-- 1-min bars for all 9 symbols
bars(symbol, ts, open, high, low, close, volume)

-- per-bar regime + strategy signal
signals(symbol, ts, regime, strategy, raw_signal, model_version)

-- completed trades
trades(id, symbol, entry_ts, entry_price, exit_ts, exit_price, qty, side, strategy, pnl)

-- equity snapshots (one per bar processed)
equity_curve(ts, cash, positions_value, total_equity)

-- model versioning
model_versions(version, trained_at, val_sharpe, notes)

-- latest tick per symbol — Realtime enabled, powers Market Watch panel
live_quotes(symbol, ts, last_price, change_pct, volume)
```

Supabase **Realtime** is enabled on `live_quotes` and `equity_curve` — the dashboard subscribes via WebSocket without polling.

---

## 11. Dashboard Requirements (Next.js + Recharts, on Vercel)

### Market Watch Panel (persistent, top of every page)

Real-time live tile for each of the 9 symbols, updating via Supabase Realtime:

```
[ SPY  $485.20  +0.42% ▲ ]   [ QQQ  $415.10  -0.15% ▼ ]   [ IWM  $198.44  +0.88% ▲ ]
[ AAPL $189.90  +1.10% ▲ ]   [ NVDA $875.33  +2.40% ▲ ]   [ MSFT $408.10  +0.55% ▲ ]
[ AMZN $178.55  -0.20% ▼ ]   [ JPM  $202.10  +0.30% ▲ ]   [ META $492.80  +1.80% ▲ ]
```

Each tile shows: last price, % change from prior close, colour-coded regime badge (🔵 Trend / 🟡 Range / 🔴 Breakout / ⚪ Flat), mini 20-bar sparkline.

### Pages

- **Overview:** equity curve vs. SPY buy-and-hold benchmark; total P&L; regime grid for all 9 symbols.
- **Positions:** open positions, unrealized P&L, entry price/time, current price (live).
- **Trade Log:** filterable table of closed trades; per-strategy win rate; per-symbol P&L breakdown.
- **Model:** current model version, last retrained date, validation Sharpe.

Data: Supabase Realtime for live quotes + equity; Supabase REST for historical tables.

---

## 12. Backtesting Requirements

- Runs offline against historical 1-min bar data — no network calls beyond initial data pull.
- Bar cadence matches live cadence (1-minute) — no mismatch between backtest and live.
- Produces: equity curve, per-trade log, win rate, Sharpe, max drawdown, per-strategy P&L attribution, per-symbol P&L attribution.
- Bit-for-bit reproducible given the same model file + date range.

---

## 13. Free Stack Summary

| Layer | Tool | Free tier notes |
|---|---|---|
| Live data | **Alpaca Markets** (free account) | Free WebSocket stream for US equities; no funded account required |
| Live data fallback | `yfinance` 60-sec polling | Unofficial but works; automatic fallback |
| Historical / training | `yfinance` bulk download | Same library; no format mismatch |
| Macro features | FRED free API | VIX, yields — no key needed |
| **Agent hosting** | **Fly.io free tier** | 3 shared-CPU VMs; scale to zero outside market hours |
| Scheduler (retraining only) | GitHub Actions | Unlimited on public repo; weekly retrain cron only |
| Database + Realtime | **Supabase** free tier | 500 MB DB + Realtime WebSocket included free |
| Frontend hosting | Vercel | Free for personal projects |
| ML training compute | Google Colab | For periodic retraining runs |

**Total monthly cost: $0**

---

## 14. Build Phases

1. **Phase 1 — Backtest engine:** data pull (1-min bars), feature engineering, model training, regime router, paper broker, backtest report (CLI, no web). Prove it works offline first.
2. **Phase 2 — Live feed integration:** wire Alpaca WebSocket → rolling 200-bar buffer → features → model inference → paper broker. Run locally during market hours, log to console.
3. **Phase 3 — Persistence:** write bars, signals, trades, equity snapshots, live quotes to Supabase. Enable Realtime on `live_quotes` and `equity_curve`.
4. **Phase 4 — Dashboard:** Next.js app with Market Watch panel (Realtime), equity curve, positions page, trade log.
5. **Phase 5 — Deployment:** containerize agent (Docker), deploy to Fly.io, configure start/stop schedule around market hours (9:25 AM – 4:01 PM ET).
6. **Phase 6 — Retraining automation:** weekly retrain GitHub Actions workflow, model versioning, auto-deploy of new `.pkl` to Fly.io.

---

## 15. Risks / Honest Caveats

- **Alpaca WebSocket reliability:** free tier may have occasional gaps or rate limits during high-volatility days. The `yfinance` 60-second polling fallback handles this; log every gap event and pause signal generation during it — never trade on stale data.
- **1-minute bar ML noise:** regime labels are noisier at 1-minute cadence than daily. Expect lower label quality and potentially more false signals — the circuit-breaker (2% daily drawdown halt) is a hard safeguard.
- **Lookahead bias:** the rolling buffer must never include the current (incomplete) bar's close in feature computation — only fully closed bars.
- **Free-tier limits:** Fly.io and Supabase free tiers are generous but finite. If you hit limits, the cheapest upgrade (Fly.io starter plan) is ~$1–2/month.
- **Model drift:** regime regimes shift. Weekly retraining helps but isn't a cure-all.
- This is a learning/demo project, not investment advice. Do not use for real capital without extensive additional validation.