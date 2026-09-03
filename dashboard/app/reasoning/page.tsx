"use client";
import { useEffect, useState } from "react";
import { fetchSignals, TradingSignal } from "@/lib/supabase";

export default function ReasoningPage() {
  const [signals, setSignals] = useState<TradingSignal[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSignals(500).then((data) => {
      setSignals(data);
      setLoading(false);
    });
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">
            Bot <span className="text-blue-500">Reasoning</span>
          </h1>
          <p className="text-slate-400 mt-1">
            Review the internal decisions of the trading agent across all live market evaluations.
          </p>
        </div>
      </div>

      <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden shadow-lg">
        <div className="overflow-x-auto w-full">
          <table className="w-full text-sm text-left text-slate-300">
            <thead className="text-xs uppercase bg-slate-950 text-slate-400 border-b border-slate-800">
              <tr>
                <th className="px-6 py-4 font-semibold tracking-wider">Time</th>
                <th className="px-6 py-4 font-semibold tracking-wider">Symbol</th>
                <th className="px-6 py-4 font-semibold tracking-wider">Regime</th>
                <th className="px-6 py-4 font-semibold tracking-wider">Strategy</th>
                <th className="px-6 py-4 font-semibold tracking-wider">Action</th>
                <th className="px-6 py-4 font-semibold tracking-wider">Reasoning</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-slate-500">
                    Loading logs...
                  </td>
                </tr>
              ) : signals.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-slate-500">
                    No signals found.
                  </td>
                </tr>
              ) : (
                signals.map((sig) => (
                  <tr key={sig.id} className="hover:bg-slate-800/50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-slate-400">
                      {new Date(sig.ts).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 font-bold text-white">{sig.symbol}</td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 bg-slate-800 border border-slate-700 rounded text-xs text-slate-300">
                        {sig.regime}
                      </span>
                    </td>
                    <td className="px-6 py-4 capitalize font-mono text-xs">{sig.strategy}</td>
                    <td className="px-6 py-4">
                      <span
                        className={`font-semibold ${
                          sig.raw_signal === "BUY" ? "text-emerald-500" :
                          sig.raw_signal === "SELL" || sig.raw_signal === "CLOSE" ? "text-red-500" :
                          "text-slate-500"
                        }`}
                      >
                        {sig.raw_signal}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-400 max-w-md truncate" title={sig.reason}>
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
