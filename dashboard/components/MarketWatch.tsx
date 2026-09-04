"use client";
// components/MarketWatch.tsx — Live 9-symbol market watch ticker bar
// Updates in real-time via Supabase Realtime WebSocket

import { useEffect, useState, useRef } from "react";
import { subscribeToLiveQuotes, LiveQuote } from "@/lib/supabase";

const REGIME_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  TREND_UP:   { label: "↑ UP",    color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/20" },
  TREND_DOWN: { label: "↓ DOWN",  color: "text-rose-400",    bg: "bg-rose-500/10 border-rose-500/20"     },
  RANGE:      { label: "⟺ RANG",  color: "text-amber-400",   bg: "bg-amber-500/10 border-amber-500/20"   },
  BREAKOUT:   { label: "⚡ BRK",   color: "text-blue-400",    bg: "bg-blue-500/10 border-blue-500/20"    },
  FLAT:       { label: "— FLAT",  color: "text-slate-400",   bg: "bg-slate-800 border-slate-700/50"      },
};

function SparkLine({ data, isUp }: { data: number[], isUp: boolean }) {
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
  
  const strokeColor = isUp ? "#10b981" : "#f43f5e"; // Emerald vs Rose

  return (
    <svg width={w} height={h} className="opacity-90 overflow-visible">
      {/* Glow effect */}
      <filter id="glow">
        <feGaussianBlur stdDeviation="1.5" result="coloredBlur"/>
        <feMerge>
          <feMergeNode in="coloredBlur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
      
      {/* Area under curve */}
      <polygon points={`0,${h} ${pts} ${w},${h}`} fill={`url(#gradient-${isUp ? 'up' : 'down'})`} className="opacity-30" />
      
      {/* The line itself */}
      <polyline points={pts} fill="none"
        stroke={strokeColor} strokeWidth="1.5"
        strokeLinejoin="round" strokeLinecap="round" 
        filter="url(#glow)" />
        
      {/* Gradients */}
      <defs>
        <linearGradient id="gradient-up" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#10b981" stopOpacity="0.8" />
          <stop offset="100%" stopColor="#10b981" stopOpacity="0" />
        </linearGradient>
        <linearGradient id="gradient-down" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#f43f5e" stopOpacity="0.8" />
          <stop offset="100%" stopColor="#f43f5e" stopOpacity="0" />
        </linearGradient>
      </defs>
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
      relative overflow-hidden flex flex-col gap-2 rounded-xl min-w-[160px] p-3 
      bg-slate-900/60 backdrop-blur border transition-all duration-300 group cursor-default
      ${flash === "up"   ? "border-emerald-500/50 shadow-[0_0_15px_rgba(16,185,129,0.2)]" : 
        flash === "down" ? "border-rose-500/50 shadow-[0_0_15px_rgba(244,63,94,0.2)]" : 
                           "border-white/5 hover:bg-slate-800/60"}
    `}>
      {/* Symbol + regime badge */}
      <div className="flex items-center justify-between gap-3 z-10">
        <span className="text-sm font-bold text-white tracking-wide">{quote.symbol}</span>
        <span className={`text-[9px] px-1.5 py-0.5 rounded border font-bold uppercase tracking-wider ${regime.color} ${regime.bg}`}>
          {regime.label}
        </span>
      </div>

      {/* Price + Sparkline */}
      <div className="flex items-end justify-between z-10 mt-1">
        <div>
          <div className={`text-base font-mono font-bold tabular-nums leading-none transition-colors duration-300
            ${flash === "up" ? "text-emerald-400" : flash === "down" ? "text-rose-400" : "text-slate-100"}`}>
            ${quote.price.toFixed(2)}
          </div>
          <span className={`text-xs font-mono font-semibold tabular-nums mt-1 block ${isUp ? "text-emerald-500" : "text-rose-500"}`}>
            {isUp ? "+" : ""}{quote.change_pct.toFixed(2)}%
          </span>
        </div>
        <div className="ml-2">
          <SparkLine data={history} isUp={isUp} />
        </div>
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
      <div className="flex items-center gap-3 text-slate-400 text-sm font-medium py-4 px-6 border-b border-white/5 bg-slate-900/50 backdrop-blur">
        <span className="w-2 h-2 rounded-full bg-slate-500 animate-pulse" />
        Connecting to market data stream...
      </div>
    );
  }

  return (
    <div className="w-full overflow-x-auto custom-scrollbar border-b border-white/5 bg-slate-950/50 backdrop-blur">
      <div className="flex gap-4 px-6 py-3 min-w-full w-max">
        {quotes.map((q) => (
          <div key={q.symbol} className="flex-1 min-w-[200px]">
            <QuoteTile quote={q} history={history[q.symbol] ?? []} />
          </div>
        ))}
      </div>
    </div>
  );
}
