"use client";
// components/RegimeGrid.tsx — Colour-coded regime badge list for the sidebar

import { useEffect, useState } from "react";
import { subscribeToLiveQuotes, LiveQuote } from "@/lib/supabase";
import { Info, BarChart2 } from "lucide-react";

const REGIME_STYLES: Record<string, { label: string; border: string; bg: string; text: string; dot: string; shadow: string }> = {
  TREND_UP:   { label: "Trend Up",   border: "border-emerald-500/20", bg: "bg-emerald-500/10", text: "text-emerald-400", dot: "bg-emerald-500", shadow: "shadow-emerald-500/20" },
  TREND_DOWN: { label: "Trend Down", border: "border-rose-500/20",    bg: "bg-rose-500/10",    text: "text-rose-400",    dot: "bg-rose-500",    shadow: "shadow-rose-500/20" },
  RANGE:      { label: "Range",      border: "border-amber-500/20",   bg: "bg-amber-500/10",   text: "text-amber-400",   dot: "bg-amber-500",   shadow: "shadow-amber-500/20" },
  BREAKOUT:   { label: "Breakout",   border: "border-blue-500/20",    bg: "bg-blue-500/10",    text: "text-blue-400",    dot: "bg-blue-500",    shadow: "shadow-blue-500/20" },
  FLAT:       { label: "Flat",       border: "border-slate-700/50",   bg: "bg-slate-800/50",   text: "text-slate-400",   dot: "bg-slate-500",   shadow: "shadow-transparent" },
};

function RegimeCard({ quote }: { quote: LiveQuote }) {
  const style = REGIME_STYLES[quote.regime] ?? REGIME_STYLES.FLAT;
  const isUp  = quote.change_pct >= 0;

  return (
    <div className={`
      relative overflow-hidden flex flex-col p-4 rounded-xl
      border ${style.border} bg-slate-900/40 backdrop-blur hover:bg-slate-800/60
      transition-all duration-300 cursor-default group
    `}>
      {/* Subtle background glow based on regime */}
      <div className={`absolute -right-4 -top-4 w-16 h-16 rounded-full blur-2xl opacity-20 transition-opacity group-hover:opacity-40 ${style.dot}`} />
      
      <div className="flex items-center justify-between mb-3 z-10">
        <h3 className="text-sm font-bold text-white tracking-wide">{quote.symbol}</h3>
        <div className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${style.bg} ${style.text}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${style.dot} shadow-[0_0_8px_currentColor]`} />
          {style.label}
        </div>
      </div>
      
      <div className="flex items-end justify-between mt-auto z-10">
        <div>
          <p className="text-xs font-medium text-slate-500 mb-0.5">Last Price</p>
          <p className="text-lg font-mono font-medium text-slate-200">
            ${quote.price.toFixed(2)}
          </p>
        </div>
        <div className="text-right">
          <p className={`text-xs font-mono font-medium ${isUp ? "text-emerald-400" : "text-rose-400"}`}>
            {isUp ? "+" : ""}{quote.change_pct.toFixed(2)}%
          </p>
        </div>
      </div>
    </div>
  );
}

export default function RegimeGrid() {
  const [quotes, setQuotes] = useState<LiveQuote[]>([]);

  useEffect(() => {
    const unsub = subscribeToLiveQuotes(setQuotes);
    return unsub;
  }, []);

  return (
    <div className="flex-1 rounded-2xl border border-white/5 bg-slate-900/60 backdrop-blur p-6 flex flex-col h-full">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-widest flex items-center gap-2">
            <BarChart2 className="w-4 h-4" />
            Market State
          </h2>
          <p className="text-xs text-slate-500 mt-1">AI-detected regimes across assets</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto pr-2 -mr-2 space-y-3 custom-scrollbar">
        {quotes.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 space-y-3 py-8">
            <div className="w-10 h-10 rounded-full border border-slate-700/50 flex items-center justify-center bg-slate-800/30">
              <Info className="w-5 h-5 text-slate-400" />
            </div>
            <span className="w-2 h-2 rounded-full bg-slate-600 animate-pulse" />
            <p className="text-slate-500 text-sm font-medium">Waiting for data stream...</p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-1 gap-3">
          {quotes.map((q) => <RegimeBadge key={q.symbol} quote={q} />)}
        </div>
      )}
    </div>
  );
}
