"use client";
// components/PositionsTable.tsx — Open positions with live unrealized P&L

import { useEffect, useState } from "react";
import { subscribeToLiveQuotes, fetchTrades, LiveQuote } from "@/lib/supabase";

interface OpenPosition {
  symbol:      string;
  entry_price: number;
  qty:         number;
  strategy:    string;
  entry_ts:    string;
}

interface PositionsTableProps {
  positions: OpenPosition[];
}

export default function PositionsTable({ positions }: PositionsTableProps) {
  const [quotes, setQuotes] = useState<Record<string, LiveQuote>>({});

  useEffect(() => {
    const unsub = subscribeToLiveQuotes((q: LiveQuote[]) => {
      const map: Record<string, LiveQuote> = {};
      q.forEach((quote: LiveQuote) => (map[quote.symbol] = quote));
      setQuotes(map);
    });
    return unsub;
  }, []);

  if (positions.length === 0) {
    return (
      <div className="rounded-2xl border border-white/5 bg-slate-900/60 backdrop-blur p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Open Positions</h2>
        <p className="text-slate-500 text-sm py-4 text-center">No open positions</p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-white/5 bg-slate-900/60 backdrop-blur p-6">
      <h2 className="text-lg font-semibold text-white mb-4">Open Positions</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-slate-500 border-b border-white/5">
              <th className="text-left pb-3 font-medium">Symbol</th>
              <th className="text-right pb-3 font-medium">Qty</th>
              <th className="text-right pb-3 font-medium">Entry</th>
              <th className="text-right pb-3 font-medium">Current</th>
              <th className="text-right pb-3 font-medium">Unr. P&L</th>
              <th className="text-left pb-3 font-medium pl-4">Strategy</th>
              <th className="text-left pb-3 font-medium pl-4">Since</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((pos) => {
              const quote    = quotes[pos.symbol];
              const current  = quote?.last_price ?? pos.entry_price;
              const pnl      = (current - pos.entry_price) * pos.qty;
              const pnlPct   = ((current - pos.entry_price) / pos.entry_price) * 100;
              const isUp     = pnl >= 0;
              return (
                <tr key={pos.symbol} className="border-b border-white/5 hover:bg-white/2 transition-colors">
                  <td className="py-3 font-bold text-white">{pos.symbol}</td>
                  <td className="py-3 text-right text-slate-300 tabular-nums">{pos.qty.toFixed(2)}</td>
                  <td className="py-3 text-right text-slate-300 tabular-nums">${pos.entry_price.toFixed(2)}</td>
                  <td className="py-3 text-right text-white tabular-nums font-medium">${current.toFixed(2)}</td>
                  <td className={`py-3 text-right tabular-nums font-semibold ${isUp ? "text-emerald-400" : "text-red-400"}`}>
                    {isUp ? "+" : ""}${pnl.toFixed(2)}
                    <span className="text-xs ml-1">({isUp ? "+" : ""}{pnlPct.toFixed(2)}%)</span>
                  </td>
                  <td className="py-3 pl-4">
                    <span className="px-2 py-0.5 rounded-full bg-slate-700 text-slate-300 text-xs">
                      {pos.strategy}
                    </span>
                  </td>
                  <td className="py-3 pl-4 text-slate-500 text-xs">
                    {new Date(pos.entry_ts).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
