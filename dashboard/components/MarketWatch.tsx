"use client";
// components/MarketWatch.tsx — Live 9-symbol market watch ticker bar
// Updates in real-time via Supabase Realtime WebSocket

import { useEffect, useState, useRef } from "react";
import { subscribeToLiveQuotes, LiveQuote } from "@/lib/supabase";

const REGIME_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  TREND_UP:   { label: "↑ UP",    color: "text-emerald-500", bg: "bg-emerald-500/10" },
  TREND_DOWN: { label: "↓ DOWN",  color: "text-red-500",     bg: "bg-red-500/10"     },
  RANGE:      { label: "⟺ RANG",  color: "text-amber-500",   bg: "bg-amber-500/10"   },
  BREAKOUT:   { label: "⚡ BRK",   color: "text-blue-500",    bg: "bg-blue-500/10"    },
  FLAT:       { label: "— FLAT",  color: "text-slate-400",   bg: "bg-slate-800"      },
};

function SparkLine({ data }: { data: number[] }) {
  if (data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const w = 64, h = 24;
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / range) * h;
    return `${x},${y}`;
  }).join(" ");
  const isUp = data[data.length - 1] >= data[0];
  return (
    <svg width={w} height={h} className="opacity-80">
      <polyline points={pts} fill="none"
        stroke={isUp ? "#10b981" : "#ef4444"} strokeWidth="1.5"
        strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

function QuoteTile({ quote, history }: { quote: LiveQuote; history: number[] }) {
  const isUp       = quote.change_pct >= 0;
  const regime     = REGIME_CONFIG[quote.regime] ?? REGIME_CONFIG.FLAT;
  const prevPrice  = useRef(quote.price);
  const [flash, setFlash] = useState<"up" | "down" | null>(null);

  useEffect(() => {
    if (quote.price !== prevPrice.current) {
      setFlash(quote.price > prevPrice.current ? "up" : "down");
      prevPrice.current = quote.price;
      const t = setTimeout(() => setFlash(null), 600);
      return () => clearTimeout(t);
    }
  }, [quote.price]);

  return (
    <div className={`
      flex flex-col gap-1.5 rounded-lg border p-3 min-w-[150px]
      bg-slate-900 transition-colors duration-200
      ${flash === "up"   ? "border-emerald-500/50" : "border-slate-800"}
      ${flash === "down" ? "border-red-500/50" : ""}
    `}>
      {/* Symbol + regime badge */}
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-semibold text-white tracking-wide">{quote.symbol}</span>
        <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium font-mono ${regime.color} ${regime.bg}`}>
          {regime.label}
        </span>
      </div>

      {/* Price */}
      <div className={`text-base font-mono font-semibold tabular-nums transition-colors duration-300
        ${flash === "up" ? "text-emerald-400" : flash === "down" ? "text-red-400" : "text-slate-100"}`}>
        ${quote.price.toFixed(2)}
      </div>

      {/* Change % + sparkline */}
      <div className="flex items-center justify-between">
        <span className={`text-xs font-mono font-medium tabular-nums ${isUp ? "text-emerald-500" : "text-red-500"}`}>
          {isUp ? "+" : ""}{quote.change_pct.toFixed(2)}%
        </span>
        <SparkLine data={history} />
      </div>
    </div>
  );
}

export default function MarketWatch() {
  const [quotes, setQuotes]   = useState<LiveQuote[]>([]);
  const [history, setHistory] = useState<Record<string, number[]>>({});

  useEffect(() => {
    const unsub = subscribeToLiveQuotes((q: LiveQuote[]) => {
      setQuotes(q);
      setHistory((prev) => {
        const next = { ...prev };
        q.forEach((quote: LiveQuote) => {
          const arr = [...(next[quote.symbol] ?? []), quote.price].slice(-20);
          next[quote.symbol] = arr;
        });
        return next;
      });
    });
    return unsub;
  }, []);

  if (quotes.length === 0) {
    return (
      <div className="flex items-center gap-2 text-slate-400 text-sm font-medium py-3 px-6">
        <span className="w-2 h-2 rounded-full bg-slate-500 animate-pulse" />
        Connecting to market data...
      </div>
    );
  }

  return (
    <div className="w-full overflow-x-auto scrollbar-none border-b border-slate-800">
      <div className="flex gap-3 px-6 py-3 min-w-max">
        {quotes.map((q) => (
          <QuoteTile key={q.symbol} quote={q} history={history[q.symbol] ?? []} />
        ))}
      </div>
    </div>
  );
}
