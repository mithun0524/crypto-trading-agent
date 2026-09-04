"use client";
import { useEffect, useState, useMemo } from "react";
import { fetchTrades, subscribeToTrades, Trade } from "@/lib/supabase";
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from "recharts";
import { Activity, RefreshCw } from "lucide-react";

export default function TradeLog() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [filter, setFilter] = useState<string>("all");
  const [symFilter, setSymFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTrades(200).then((t) => { setTrades(t); setLoading(false); });
    const unsub = subscribeToTrades((newTrades) => {
      setTrades(newTrades);
    });
    return unsub;
  }, []);

  const [page, setPage] = useState(1);
  const PAGE_SIZE = 25;

  const strategies = [...new Set(trades.map((t) => t.strategy))].filter(Boolean);
  const symbols = [...new Set(trades.map((t) => t.symbol))].sort();

  const filtered = useMemo(() => {
    return trades.filter((t) => {
      if (filter !== "all" && t.strategy !== filter) return false;
      if (symFilter !== "all" && t.symbol !== symFilter) return false;
      return true;
    });
  }, [trades, filter, symFilter]);

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [filter, symFilter]);

  const totalPnl = filtered.reduce((s, t) => s + t.pnl, 0);
  const wins = filtered.filter(t => t.pnl > 0).length;
  const winRate = filtered.length > 0 ? (wins / filtered.length) * 100 : 0;
  
  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paginatedTrades = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  // Chart Data Preparation
  const chartData = useMemo(() => {
    let cumulative = 0;
    return [...filtered].reverse().map((t, index) => {
      cumulative += t.pnl;
      return {
        name: `T${index + 1}`,
        ts: new Date(t.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        pnl: t.pnl,
        cumulative: cumulative,
        strategy: t.strategy,
      };
    });
  }, [filtered]);

  const strategyData = useMemo(() => {
    return strategies.map(s => {
      const sTrades = trades.filter(t => t.strategy === s);
      return {
        name: s.replace("_", " "),
        pnl: sTrades.reduce((acc, t) => acc + t.pnl, 0),
        count: sTrades.length
      };
    }).sort((a, b) => b.pnl - a.pnl);
  }, [trades, strategies]);

  return (
    <div className="rounded-2xl border border-white/5 bg-slate-900/60 backdrop-blur p-6 space-y-8">
      
      {/* Header & Stats */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Activity className="w-5 h-5 text-emerald-400" />
            Trade Analytics
          </h2>
          <p className="text-sm text-slate-400 mt-1">Real-time performance and strategy breakdown</p>
        </div>
        <div className="flex gap-4">
          <div className="bg-slate-800/50 rounded-xl p-3 border border-white/5">
            <p className="text-xs text-slate-500 font-medium">Total P&L</p>
            <p className={`text-lg font-bold tabular-nums ${totalPnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
              {totalPnl >= 0 ? "+" : "-"}${Math.abs(totalPnl).toFixed(2)}
            </p>
          </div>
          <div className="bg-slate-800/50 rounded-xl p-3 border border-white/5">
            <p className="text-xs text-slate-500 font-medium">Win Rate</p>
            <p className="text-lg font-bold text-white tabular-nums">{winRate.toFixed(1)}%</p>
          </div>
        </div>
      </div>

      {/* Visualizations */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Cumulative PnL Area Chart */}
        <div className="lg:col-span-2 h-[260px] bg-slate-950/30 rounded-xl border border-white/5 p-4 flex flex-col">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">Cumulative P&L</h3>
          {filtered.length === 0 ? (
            <div className="flex-1 flex items-center justify-center text-sm text-slate-600">No data to display</div>
          ) : (
            <div className="flex-1">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 5, right: 0, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorPnL" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={totalPnl >= 0 ? "#10b981" : "#f43f5e"} stopOpacity={0.3}/>
                      <stop offset="95%" stopColor={totalPnl >= 0 ? "#10b981" : "#f43f5e"} stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff0a" vertical={false} />
                  <XAxis dataKey="ts" stroke="#ffffff40" fontSize={11} tickMargin={10} minTickGap={30} />
                  <YAxis stroke="#ffffff40" fontSize={11} tickFormatter={(val) => `$${val}`} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #ffffff1a", borderRadius: "8px", fontSize: "12px" }}
                    itemStyle={{ color: "#f8fafc" }}
                  />
                  <Area type="monotone" dataKey="cumulative" stroke={totalPnl >= 0 ? "#10b981" : "#f43f5e"} strokeWidth={2} fill="url(#colorPnL)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Strategy Bar Chart */}
        <div className="lg:col-span-1 h-[260px] bg-slate-950/30 rounded-xl border border-white/5 p-4 flex flex-col">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">P&L by Strategy</h3>
          {strategyData.length === 0 ? (
            <div className="flex-1 flex items-center justify-center text-sm text-slate-600">No data</div>
          ) : (
            <div className="flex-1">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={strategyData} layout="vertical" margin={{ top: 0, right: 20, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff0a" horizontal={false} />
                  <XAxis type="number" stroke="#ffffff40" fontSize={11} />
                  <YAxis dataKey="name" type="category" width={80} stroke="#ffffff40" fontSize={10} />
                  <Tooltip 
                    cursor={{fill: '#ffffff0a'}}
                    contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #ffffff1a", borderRadius: "8px", fontSize: "12px" }}
                  />
                  <Bar dataKey="pnl" radius={[0, 4, 4, 0]}>
                    {strategyData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.pnl >= 0 ? "#34d399" : "#fb7185"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-white/5 pt-6">
        {/* Filters */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Strategy:</span>
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="bg-slate-950 border border-white/10 rounded-lg text-sm text-slate-300 px-3 py-1.5 outline-none focus:border-indigo-500/50 transition-colors"
              >
                <option value="all">All Strategies</option>
                {strategies.map((s) => (
                  <option key={s} value={s}>{s.replace("_", " ")}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Symbol:</span>
              <select
                value={symFilter}
                onChange={(e) => setSymFilter(e.target.value)}
                className="bg-slate-950 border border-white/10 rounded-lg text-sm text-slate-300 px-3 py-1.5 outline-none focus:border-indigo-500/50 transition-colors"
              >
                <option value="all">All Assets</option>
                {symbols.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            {loading && <RefreshCw className="w-4 h-4 text-slate-500 animate-spin" />}
          </div>
          
          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center gap-2">
              <button 
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1.5 text-xs font-medium text-slate-300 bg-slate-950 border border-white/10 rounded-md hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Prev
              </button>
              <span className="text-xs text-slate-500 font-medium">Page {page} of {totalPages}</span>
              <button 
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1.5 text-xs font-medium text-slate-300 bg-slate-950 border border-white/10 rounded-md hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Next
              </button>
            </div>
          )}
        </div>

        {/* Detailed Trades Table */}
        <div className="overflow-x-auto rounded-xl border border-white/5 bg-slate-950/20 max-h-[400px] overflow-y-auto relative">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-slate-900/95 backdrop-blur border-b border-white/5 text-slate-400 sticky top-0 z-10">
              <tr>
                <th className="px-4 py-3 font-medium">Time</th>
                <th className="px-4 py-3 font-medium">Symbol</th>
                <th className="px-4 py-3 font-medium">Strategy</th>
                <th className="px-4 py-3 font-medium text-right">Price</th>
                <th className="px-4 py-3 font-medium text-right">Qty</th>
                <th className="px-4 py-3 font-medium text-right">P&L</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-slate-300">
              {paginatedTrades.map((t) => (
                <tr key={t.id} className="hover:bg-white/[0.02] transition-colors">
                  <td className="px-4 py-2.5 text-slate-500">
                    {new Date(t.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                  </td>
                  <td className="px-4 py-2.5 font-medium text-white">{t.symbol}</td>
                  <td className="px-4 py-2.5">
                    <span className="bg-slate-800/50 text-slate-300 px-2 py-0.5 rounded-md text-xs border border-white/5">
                      {t.strategy}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-right font-medium">${t.price.toFixed(2)}</td>
                  <td className="px-4 py-2.5 text-right text-slate-400">
                    <span className={t.side === "BUY" || t.side === "LONG" ? "text-emerald-400/80" : "text-rose-400/80"}>{t.side}</span> {t.qty.toFixed(4)}
                  </td>
                  <td className={`px-4 py-2.5 text-right font-medium ${
                    t.pnl > 0 ? "text-emerald-400" : t.pnl < 0 ? "text-rose-400" : "text-slate-500"
                  }`}>
                    {t.pnl > 0 ? "+" : ""}{t.pnl === 0 ? "-" : `$${t.pnl.toFixed(2)}`}
                  </td>
                </tr>
              ))}
              {paginatedTrades.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                    No trades match the selected filters
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
