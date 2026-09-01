"""
backtest/engine.py — Offline backtest runner.

Replays historical bars through the full pipeline:
  feature engineering → regime model → strategy router → paper broker

Outputs:
  - Equity curve (CSV + console print)
  - Per-trade log (CSV)
  - Summary metrics: Sharpe, max drawdown, win rate, per-strategy P&L

Usage:
    python -m agent.backtest.engine
    python -m agent.backtest.engine --start 2024-01-01 --end 2024-06-30 --interval 1h
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import SYMBOLS, WARM_UP_BARS, STARTING_CASH
from data.history import download_bars, load_cached
from data.fred import get_latest_macro
from features.engineer import compute_features
from model.predict import predict
from strategy.router import route
from broker.paper import PaperBroker


# ── Metrics helpers ────────────────────────────────────────────────────────────

def _sharpe(equity_curve: list[float], bars_per_year: int = 252 * 6 * 60) -> float:
    rets = pd.Series(equity_curve).pct_change().dropna()
    if rets.std() == 0:
        return 0.0
    return float((rets.mean() / rets.std()) * np.sqrt(bars_per_year))


def _max_drawdown(equity_curve: list[float]) -> float:
    eq   = pd.Series(equity_curve)
    peak = eq.cummax()
    dd   = (eq - peak) / peak
    return float(dd.min())


# ── Main backtest function ─────────────────────────────────────────────────────

def run_backtest(
    symbols: list[str] | None = None,
    start:   str | None = None,
    end:     str | None = None,
    interval: str = "1h",
) -> dict:
    """
    Run the full backtest and return a results dict.
    """
    if symbols is None:
        symbols = SYMBOLS

    logger.info("=" * 60)
    logger.info("AlgoPaper Backtest Engine")
    logger.info("=" * 60)

    # ── Load data ──────────────────────────────────────────────────────────────
    logger.info(f"Loading {interval} bars for {len(symbols)} symbols ...")
    all_bars: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        cached = load_cached(sym, interval)
        if cached is None:
            logger.info(f"  {sym}: not cached, downloading ...")
            bars_map = download_bars([sym], interval=interval, force=False)
            cached = bars_map.get(sym)
        if cached is None or len(cached) < WARM_UP_BARS + 50:
            logger.warning(f"  {sym}: insufficient data, skipping")
            continue
        # Optional date filter
        if start:
            cached = cached[cached.index >= start]
        if end:
            cached = cached[cached.index <= end]
        all_bars[sym] = cached
        logger.info(f"  {sym}: {len(cached)} bars")

    if not all_bars:
        raise RuntimeError("No bars loaded — run data download first.")

    # ── Macro context ──────────────────────────────────────────────────────────
    macro = get_latest_macro()
    vix_level = macro.get("VIX", 18.0)

    # ── Align all symbols on a common bar index ────────────────────────────────
    all_indices = [df.index for df in all_bars.values()]
    common_idx  = all_indices[0]
    for idx in all_indices[1:]:
        common_idx = common_idx.intersection(idx)
    common_idx = common_idx.sort_values()
    logger.info(f"Common bar index: {len(common_idx)} bars")

    if len(common_idx) < WARM_UP_BARS + 50:
        raise RuntimeError("Not enough common bars after intersection.")

    # ── Precompute features for each symbol ────────────────────────────────────
    logger.info("Computing features ...")
    all_features: dict[str, pd.DataFrame] = {}
    for sym, bars in all_bars.items():
        feat = compute_features(bars, vix_level=vix_level, vix_roc=0.0)
        all_features[sym] = feat

    # ── Initialise broker ──────────────────────────────────────────────────────
    broker = PaperBroker(starting_cash=STARTING_CASH)

    # ── State tracking ─────────────────────────────────────────────────────────
    equity_curve:  list[dict] = []
    per_bar_signals: list[dict] = []
    strategy_pnl:  defaultdict[str, float] = defaultdict(float)
    current_prices: dict[str, float] = {}

    # ── Walk forward through bars ──────────────────────────────────────────────
    bars_processed = 0
    for i, ts in enumerate(common_idx):
        if i < WARM_UP_BARS:
            continue   # skip warmup period

        # ── Build current prices dict ──────────────────────────────────────────
        for sym in all_bars:
            if ts in all_bars[sym].index:
                current_prices[sym] = float(all_bars[sym].loc[ts, "close"])

        # ── Fill pending orders at this bar's open ────────────────────────────
        next_opens = {
            sym: float(all_bars[sym].loc[ts, "open"])
            for sym in all_bars if ts in all_bars[sym].index
        }
        filled_trades = broker.fill_pending_orders(next_opens, ts, current_prices)
        for t in filled_trades:
            if t and t.strategy:
                strategy_pnl[t.strategy] += t.pnl

        # ── Generate signals for each symbol ──────────────────────────────────
        for sym in all_bars:
            if ts not in all_features[sym].index:
                continue

            # Rolling window up to current bar (exclusive of current incomplete bar)
            feat_window = all_features[sym].loc[:ts]
            if len(feat_window) < 2:
                continue

            try:
                regime, model_ver = predict(feat_window)
            except FileNotFoundError:
                logger.warning("Model not found — run train.py first")
                regime, model_ver = "FLAT", "none"

            bars_window = all_bars[sym].loc[:ts]
            open_pos    = sym in broker.positions
            signal      = route(regime, sym, feat_window, open_position=open_pos)

            curr_bar = {
                "close": float(all_bars[sym].loc[ts, "close"]),
                "open":  float(all_bars[sym].loc[ts, "open"]),
                "atr":   float(all_features[sym].loc[ts, "atr"])
                         if "atr" in all_features[sym].columns else 0.0,
            }
            broker.place_order(signal, curr_bar, current_prices, model_version=model_ver)

            per_bar_signals.append({
                "ts":       ts,
                "symbol":   sym,
                "regime":   regime,
                "strategy": signal["strategy"],
                "action":   signal["action"],
            })

        # ── Snapshot equity ────────────────────────────────────────────────────
        snap = broker.snapshot(current_prices)
        equity_curve.append({"ts": ts, **snap})
        bars_processed += 1

    # ── EOD: close all remaining positions ────────────────────────────────────
    final_ts = common_idx[-1]
    eod_trades = broker.close_all(current_prices, dt.datetime.utcnow())
    for t in eod_trades:
        strategy_pnl[t.strategy] += t.pnl

    # ── Results ────────────────────────────────────────────────────────────────
    eq_series  = [row["total_equity"] for row in equity_curve]
    sharpe     = _sharpe(eq_series)
    max_dd     = _max_drawdown(eq_series)
    broker_stats = broker.stats()

    logger.info("")
    logger.info("=" * 60)
    logger.info("BACKTEST RESULTS")
    logger.info("=" * 60)
    logger.info(f"  Bars processed : {bars_processed}")
    logger.info(f"  Start equity   : ${STARTING_CASH:,.0f}")
    logger.info(f"  End equity     : ${eq_series[-1]:,.0f}")
    logger.info(f"  Total P&L      : ${eq_series[-1] - STARTING_CASH:,.0f} ({(eq_series[-1]/STARTING_CASH-1)*100:.1f}%)")
    logger.info(f"  Sharpe ratio   : {sharpe:.3f}")
    logger.info(f"  Max drawdown   : {max_dd*100:.2f}%")
    logger.info(f"  Total trades   : {broker_stats.get('total_trades', 0)}")
    logger.info(f"  Win rate       : {broker_stats.get('win_rate', 0):.1f}%")
    logger.info(f"  Profit factor  : {broker_stats.get('profit_factor', 0):.3f}")
    logger.info("")
    logger.info("  Strategy P&L breakdown:")
    for strat, pnl in sorted(strategy_pnl.items()):
        logger.info(f"    {strat:<20} ${pnl:>10,.2f}")

    # ── Save outputs ───────────────────────────────────────────────────────────
    out_dir = Path(__file__).parent.parent / "backtest_results"
    out_dir.mkdir(exist_ok=True)

    eq_df = pd.DataFrame(equity_curve)
    eq_df.to_csv(out_dir / "equity_curve.csv", index=False)

    trades_df = pd.DataFrame([
        {
            "id": t.id, "symbol": t.symbol,
            "entry_ts": t.entry_ts, "entry_price": t.entry_price,
            "exit_ts": t.exit_ts, "exit_price": t.exit_price,
            "qty": t.qty, "side": t.side, "strategy": t.strategy,
            "pnl": t.pnl, "commission": t.commission,
        }
        for t in broker.closed_trades
    ])
    trades_df.to_csv(out_dir / "trades.csv", index=False)

    logger.success(f"  Results saved → {out_dir}/")

    return {
        "sharpe":       sharpe,
        "max_drawdown": max_dd,
        "final_equity": eq_series[-1] if eq_series else STARTING_CASH,
        "total_trades": broker_stats.get("total_trades", 0),
        "win_rate":     broker_stats.get("win_rate", 0),
        "strategy_pnl": dict(strategy_pnl),
        "equity_curve": equity_curve,
        "trades":       broker.closed_trades,
    }


def main():
    parser = argparse.ArgumentParser(description="Run AlgoPaper backtest")
    parser.add_argument("--start",    default=None, help="Start date YYYY-MM-DD")
    parser.add_argument("--end",      default=None, help="End date YYYY-MM-DD")
    parser.add_argument("--interval", default="1h", choices=["1m", "1h", "1d"],
                        help="Bar interval")
    parser.add_argument("--symbols",  nargs="*", default=None,
                        help="Symbols to backtest (default: all)")
    args = parser.parse_args()
    run_backtest(
        symbols=args.symbols,
        start=args.start,
        end=args.end,
        interval=args.interval,
    )


if __name__ == "__main__":
    main()
