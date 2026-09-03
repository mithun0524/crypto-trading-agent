"use client";
// components/TradeLog.tsx — Filterable closed trade log with per-strategy win rate

import { useEffect, useState } from "react";
import { fetchTrades, Trade } from "@/lib/supabase";

const STRATEGY_COLORS: Record<string, string> = {
  trend:           "bg-emerald-400/15 text-emerald-300",
  mean_reversion:  "bg-amber-400/15 text-amber-300",
  breakout:        "bg-violet-400/15 text-violet-300",
  flat:            "bg-slate-700 text-slate-400",
  none:            "bg-slate-700 text-slate-400",
};

function WinRateBar({ strategy, trades }: { strategy: string; trades: Trade[] }) {
  const filtered = trades.filter((t) => t.strategy === strategy);
  const wins     = filtered.filter((t) => t.pnl > 0).length;
  const winRate  = filtered.length > 0 ? (wins / filtered.length) * 100 : 0;
  const totalPnl = filtered.reduce((s, t) => s + t.pnl, 0);
  const color    = STRATEGY_COLORS[strategy] ?? STRATEGY_COLORS.none;

  return (
    <div className="flex items-center gap-3">
      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${color} min-w-[110px] text-center`}>
        {strategy.replace("_", " ")}
      </span>
      <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${winRate >= 50 ? "bg-emerald-400" : "bg-red-400"}`}
          style={{ width: `${winRate}%` }}
        />
      </div>
      <span className="text-xs text-slate-400 tabular-nums w-12 text-right">{winRate.toFixed(0)}%</span>
      <span className={`text-xs tabular-nums font-medium w-20 text-right ${totalPnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
        {totalPnl >= 0 ? "+" : ""}${totalPnl.toFixed(0)}
      </span>
      <span className="text-xs text-slate-500 w-8 text-right">{filtered.length}t</span>
    </div>
  );
}

export default function TradeLog() {
  const [trades,   setTrades]   = useState<Trade[]>([]);
  const [filter,   setFilter]   = useState<string>("all");
  const [symFilter, setSymFilter] = useState<string>("all");
  const [loading,  setLoading]  = useState(true);

  useEffect(() => {
    fetchTrades(200).then((t) => { setTrades(t); setLoading(false); });
  }, []);

  const strategies = [...new Set(trades.map((t) => t.strategy))].filter(Boolean);
  const symbols    = [...new Set(trades.map((t) => t.symbol))].sort();

  const filtered = trades.filter((t) => {
    if (filter !== "all"    && t.strategy !== filter)  return false;
    if (symFilter !== "all" && t.symbol   !== symFilter) return false;
    return true;
  });

  const totalPnl  = filtered.reduce((s, t) => s + t.pnl, 0);
  const winRate   = filtered.length > 0
    ? (filtered.filter((t) => t.pnl > 0).length / filtered.length) * 100
    : 0;

  return (
    <div className="rounded-2xl border border-white/5 bg-slate-900/60 backdrop-blur p-6 space-y-6">
      {/* Per-strategy win rates */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4">Strategy Performance</h2>
        <div className="space-y-2">
          <div className="flex items-center gap-3 text-xs text-slate-500 mb-1 pl-[126px]">
            <span className="flex-1">win rate</span>
            <span className="w-12 text-right">%</span>
            <span className="w-20 text-right">p&l</span>
            <span className="w-8 text-right">trades</span>
          </div>
          {strategies.map((s) => (
            <WinRateBar key={s} strategy={s} trades={trades} />
          ))}
          {strategies.length === 0 && (
            <p className="text-slate-500 text-sm">No closed trades yet</p>
          )}
        </div>
      </div>

      <div className="border-t border-white/5 pt-4">
        {/* Filters + summary */}
        <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
          <h2 className="text-lg font-semibold text-white">Trade Log</h2>
          <div className="flex gap-2 items-center flex-wrap">
            {/* Summary chips */}
            <span className="text-xs text-slate-400">
              {filtered.length} trades •{" "}
              <span className={totalPnl >= 0 ? "text-emerald-400" : "text-red-400"}>
                {totalPnl >= 0 ? "+" : ""}${totalPnl.toFixed(0)} P&L
              </span>
              {" "}• {winRate.toFixed(0)}% win
            </span>
            {/* Strategy filter */}
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="text-xs bg-slate-800 border border-white/10 rounded-lg px-2 py-1.5 text-slate-300"
            >
              <option value="all">All strategies</option>
              {strategies.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
            {/* Symbol filter */}
            <select
              value={symFilter}
              onChange={(e) => setSymFilter(e.target.value)}
              className="text-xs bg-slate-800 border border-white/10 rounded-lg px-2 py-1.5 text-slate-300"
            >
              <option value="all">All symbols</option>
              {symbols.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        </div>

        {/* Table */}
        {loading ? (
          <p className="text-slate-500 text-sm py-4">Loading trades...</p>
        ) : filtered.length === 0 ? (
          <p className="text-slate-500 text-sm py-4 text-center">No trades match your filters</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-500 border-b border-white/5">
                  <th className="text-left pb-3 font-medium">Symbol</th>
                  <th className="text-left pb-3 font-medium">Strategy</th>
                  <th className="text-right pb-3 font-medium">Side</th>
                  <th className="text-right pb-3 font-medium">Price</th>
                  <th className="text-right pb-3 font-medium">Qty</th>
                  <th className="text-right pb-3 font-medium">P&L</th>
                  <th className="text-left pb-3 font-medium pl-4">Time</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((t) => {
                  const isUp = t.pnl >= 0;
                  return (
                    <tr key={t.id} className="border-b border-white/5 hover:bg-white/2 transition-colors">
                      <td className="py-2.5 font-bold text-white">{t.symbol}</td>
                      <td className="py-2.5">
                        <span className={`px-2 py-0.5 rounded-full text-xs ${STRATEGY_COLORS[t.strategy] ?? STRATEGY_COLORS.none}`}>
                          {t.strategy}
                        </span>
                      </td>
                      <td className={`py-2.5 text-right font-medium ${t.side === "BUY" || t.side === "LONG" ? "text-emerald-400" : "text-red-400"}`}>
                        {t.side}
                      </td>
                      <td className="py-2.5 text-right text-slate-300 tabular-nums">${t.price.toFixed(2)}</td>
                      <td className="py-2.5 text-right text-slate-400 tabular-nums">{t.qty.toFixed(2)}</td>
                      <td className={`py-2.5 text-right tabular-nums font-semibold ${isUp ? "text-emerald-400" : "text-red-400"}`}>
                        {isUp ? "+" : ""}${t.pnl.toFixed(2)}
                      </td>
                      <td className="py-2.5 pl-4 text-slate-500 text-xs">
                        {t.ts ? new Date(t.ts).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
