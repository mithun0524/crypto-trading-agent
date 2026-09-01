"use client";
// components/RegimeGrid.tsx — Colour-coded regime badge list for the sidebar

import { useEffect, useState } from "react";
import { subscribeToLiveQuotes, LiveQuote } from "@/lib/supabase";
import { Info } from "lucide-react";

const REGIME_STYLES: Record<string, { label: string; border: string; bg: string; text: string; dot: string }> = {
  TREND_UP:   { label: "Trend Up",   border: "border-emerald-500/30 hover:border-emerald-500/60", bg: "bg-emerald-500/10", text: "text-emerald-500", dot: "bg-emerald-500" },
  TREND_DOWN: { label: "Trend Down", border: "border-red-500/30 hover:border-red-500/60",         bg: "bg-red-500/10",     text: "text-red-500",     dot: "bg-red-500" },
  RANGE:      { label: "Range",      border: "border-amber-500/30 hover:border-amber-500/60",     bg: "bg-amber-500/10",   text: "text-amber-500",   dot: "bg-amber-500" },
  BREAKOUT:   { label: "Breakout",   border: "border-blue-500/30 hover:border-blue-500/60",       bg: "bg-blue-500/10",    text: "text-blue-500",    dot: "bg-blue-500" },
  FLAT:       { label: "Flat",       border: "border-slate-700 hover:border-slate-600",           bg: "bg-slate-800",      text: "text-slate-400",   dot: "bg-slate-500" },
};

function RegimeBadge({ quote }: { quote: LiveQuote }) {
  const style = REGIME_STYLES[quote.regime] ?? REGIME_STYLES.FLAT;
  const isUp  = quote.change_pct >= 0;

  return (
    <div className={`
      flex items-center justify-between p-3.5 rounded-lg
      border ${style.border} bg-slate-900 hover:bg-slate-800
      transition-colors duration-200 cursor-default shadow-sm
    `}>
      <div className="flex items-center gap-3">
        <span className={`w-2 h-2 rounded-full ${style.dot} shadow-[0_0_8px_currentColor] opacity-80`} />
        <div>
          <p className="text-sm font-semibold text-white tracking-wide">{quote.symbol}</p>
          <div className={`mt-1 inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider ${style.bg} ${style.text}`}>
            {style.label}
          </div>
        </div>
      </div>
      <div className="text-right">
        <p className="text-sm font-mono font-medium text-slate-100">
          ${quote.last_price.toFixed(2)}
        </p>
        <p className={`text-[11px] font-mono font-medium mt-1 ${isUp ? "text-emerald-500" : "text-red-500"}`}>
          {isUp ? "+" : ""}{quote.change_pct.toFixed(2)}%
        </p>
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
    <div className="flex-1 rounded-xl border border-slate-800 bg-slate-900/50 p-4 sm:p-6 flex flex-col shadow-sm">
      <div className="flex items-start justify-between mb-5">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-slate-100">
              Market Regimes
            </h2>
            <div className="group relative">
              <Info className="w-4 h-4 text-slate-500 cursor-help hover:text-slate-300 transition-colors" />
              <div className="absolute left-1/2 -translate-x-1/2 top-full mt-2 w-48 p-2 bg-slate-800 text-xs text-slate-200 rounded-md shadow-xl opacity-0 group-hover:opacity-100 pointer-events-none transition-all z-50 text-center border border-slate-700">
                AI classifies each asset into a market regime (e.g., Trend Up, Range) in real-time.
              </div>
            </div>
          </div>
          <p className="text-slate-500 text-xs mt-1">Real-time classification</p>
        </div>
      </div>

      {quotes.length === 0 ? (
        <div className="flex-1 flex items-center justify-center min-h-[200px] border border-dashed border-slate-800 rounded-lg bg-slate-900/30">
          <div className="flex flex-col items-center gap-3">
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
