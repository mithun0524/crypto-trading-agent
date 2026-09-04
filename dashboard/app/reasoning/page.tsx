"use client";
import { useEffect, useState, useMemo } from "react";
import { fetchSignals, TradingSignal } from "@/lib/supabase";
import { BrainCircuit, RefreshCw } from "lucide-react";

export default function ReasoningPage() {
  const [signals, setSignals] = useState<TradingSignal[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 25;

  useEffect(() => {
    fetchSignals(500).then((data) => {
      setSignals(data);
      setLoading(false);
    });
  }, []);

  const totalPages = Math.ceil(signals.length / PAGE_SIZE);
  const paginatedSignals = useMemo(() => {
    return signals.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  }, [signals, page]);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/5 pb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            <BrainCircuit className="w-8 h-8 text-blue-500" />
            Bot Reasoning
          </h1>
          <p className="text-slate-400 mt-2">
            Review the internal decisions of the trading agent across all live market evaluations.
          </p>
        </div>
      </div>

      <div className="rounded-2xl border border-white/5 bg-slate-900/60 backdrop-blur p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            Signal Log
            {loading && <RefreshCw className="w-4 h-4 text-slate-500 animate-spin" />}
          </h2>
          
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

        <div className="overflow-x-auto rounded-xl border border-white/5 bg-slate-950/20 max-h-[500px] overflow-y-auto relative custom-scrollbar">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-slate-900/95 backdrop-blur border-b border-white/5 text-slate-400 sticky top-0 z-10">
              <tr>
                <th className="px-4 py-3 font-medium">Time</th>
                <th className="px-4 py-3 font-medium">Symbol</th>
                <th className="px-4 py-3 font-medium">Regime</th>
                <th className="px-4 py-3 font-medium">Strategy</th>
                <th className="px-4 py-3 font-medium">Action</th>
                <th className="px-4 py-3 font-medium">Reasoning</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-slate-300">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                    Loading logs...
                  </td>
                </tr>
              ) : paginatedSignals.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                    No signals found.
                  </td>
                </tr>
              ) : (
                paginatedSignals.map((sig) => (
                  <tr key={sig.id} className="hover:bg-white/[0.02] transition-colors group">
                    <td className="px-4 py-3 text-slate-500 text-xs">
                      {new Date(sig.ts).toLocaleString([], { dateStyle: 'short', timeStyle: 'medium' })}
                    </td>
                    <td className="px-4 py-3 font-bold text-white">{sig.symbol}</td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-slate-800 border border-white/5 text-slate-300">
                        {sig.regime}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs font-mono text-slate-400">{sig.strategy.replace("_", " ")}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${
                          sig.raw_signal === "BUY" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                          sig.raw_signal === "SELL" || sig.raw_signal === "CLOSE" ? "bg-rose-500/10 text-rose-400 border-rose-500/20" :
                          "bg-slate-800 border-white/5 text-slate-400"
                        }`}
                      >
                        {sig.raw_signal !== "HOLD" && (
                          <span className={`w-1.5 h-1.5 rounded-full ${
                            sig.raw_signal === "BUY" ? "bg-emerald-500 shadow-[0_0_8px_#10b981]" : "bg-rose-500 shadow-[0_0_8px_#f43f5e]"
                          }`} />
                        )}
                        {sig.raw_signal}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-400 text-xs max-w-sm truncate relative cursor-default" title={sig.reason}>
                      {sig.reason || "—"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
