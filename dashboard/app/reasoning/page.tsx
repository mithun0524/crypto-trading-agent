"use client";
import { useEffect, useState } from "react";
import { fetchSignals, CryptoSignal } from "@/lib/supabase";

export default function ReasoningPage() {
  const [signals, setSignals] = useState<CryptoSignal[]>([]);
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
          <h1 className="text-3xl font-bold text-white tracking-tight">Bot Reasoning Log</h1>
          <p className="text-gray-400 mt-1">Review the raw internal decisions of the trading agent, including reasons for holding.</p>
        </div>
      </div>

      <div className="bg-[#111] rounded-xl border border-white/5 overflow-hidden">
        <div className="overflow-x-auto w-full">
          <table className="w-full text-sm text-left text-gray-300">
            <thead className="text-xs uppercase bg-black/40 text-gray-400 border-b border-white/5">
              <tr>
                <th className="px-6 py-4 font-medium">Time</th>
                <th className="px-6 py-4 font-medium">Symbol</th>
                <th className="px-6 py-4 font-medium">Regime</th>
                <th className="px-6 py-4 font-medium">Strategy</th>
                <th className="px-6 py-4 font-medium">Action</th>
                <th className="px-6 py-4 font-medium">Reasoning</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                    Loading logs...
                  </td>
                </tr>
              ) : signals.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                    No signals found.
                  </td>
                </tr>
              ) : (
                signals.map((sig) => (
                  <tr key={sig.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-gray-400">
                      {new Date(sig.created_at).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 font-bold text-white">{sig.symbol}</td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 bg-white/5 rounded text-xs">{sig.regime}</span>
                    </td>
                    <td className="px-6 py-4 capitalize">{sig.strategy}</td>
                    <td className="px-6 py-4">
                      <span
                        className={\ont-medium \\}
                      >
                        {sig.action}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-gray-400 max-w-md truncate" title={sig.reason}>
                      {sig.reason}
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
