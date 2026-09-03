"use client";
// components/EquityCurve.tsx â€” Live equity curve vs SPY buy-and-hold benchmark

import { useEffect, useState } from "react";
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip
} from "recharts";
import { fetchEquityCurve, subscribeToEquity, EquityPoint } from "@/lib/supabase";
import { TrendingUp } from "lucide-react";

const STARTING_EQUITY = 100_000;

function formatCurrency(v: number) {
  return `$${v.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

function formatPct(v: number) {
  const pct = ((v - STARTING_EQUITY) / STARTING_EQUITY) * 100;
  return `${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%`;
}

interface ChartPoint {
  ts:     string;
  equity: number;
  label:  string;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 p-3 shadow-xl">
      <p className="text-slate-400 mb-2 text-xs font-medium">{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} style={{ color: p.color }} className="flex items-center justify-between gap-6 font-mono text-sm">
          <span>{p.name}</span>
          <span>{formatCurrency(p.value)} <span className="opacity-60 ml-2">[{formatPct(p.value)}]</span></span>
        </p>
      ))}
    </div>
  );
};

export default function EquityCurve() {
  const [data, setData] = useState<ChartPoint[]>([]);
  const [stats, setStats] = useState({ pnl: 0, pnlPct: 0, latest: STARTING_EQUITY });

  const processPoints = (points: EquityPoint[]) => {
    const chartData = points.map((p) => ({
      ts:     new Date(p.ts).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }),
      equity: p.total_equity,
      label:  p.ts,
    }));
    setData(chartData);
    if (chartData.length > 0) {
      const latest = chartData[chartData.length - 1].equity;
      setStats({
        pnl:    latest - STARTING_EQUITY,
        pnlPct: ((latest - STARTING_EQUITY) / STARTING_EQUITY) * 100,
        latest,
      });
    }
  };

  useEffect(() => {
    fetchEquityCurve(500).then(processPoints);
    const unsub = subscribeToEquity((point) => {
      setData((prev) => {
        const next = [
          ...prev,
          {
            ts:     new Date(point.ts).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }),
            equity: point.total_equity,
            label:  point.ts,
          },
        ].slice(-500);
        const latest = next[next.length - 1]?.equity ?? STARTING_EQUITY;
        setStats({ pnl: latest - STARTING_EQUITY, pnlPct: ((latest - STARTING_EQUITY) / STARTING_EQUITY) * 100, latest });
        return next;
      });
    });
    return unsub;
  }, []);

  const isUp = stats.pnl >= 0;
  const color = isUp ? "#10b981" : "#ef4444"; // emerald-500 or red-500

  return (
    <div className="flex-1 rounded-xl border border-slate-800 bg-slate-900/50 p-4 sm:p-6 relative flex flex-col shadow-sm">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 sm:gap-0 mb-6 sm:mb-8 relative z-10">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-slate-100">
              Portfolio Equity
            </h2>
            <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 text-[10px] font-medium uppercase tracking-wider">
              Paper
            </span>
          </div>
          <p className="text-slate-500 text-xs mt-1">Live tracking against $100K starting capital</p>
        </div>
        <div className="text-left sm:text-right">
          <p className="text-3xl sm:text-4xl font-semibold text-white font-mono tracking-tight">
            {formatCurrency(stats.latest)}
          </p>
          <div className={`flex items-center sm:justify-end gap-1.5 mt-1 text-sm font-mono font-medium`} style={{ color }}>
            <TrendingUp className={`w-4 h-4 ${!isUp && "rotate-180"}`} />
            <span>{isUp ? "+" : ""}{formatCurrency(stats.pnl)}</span>
            <span className="opacity-75">({isUp ? "+" : ""}{stats.pnlPct.toFixed(2)}%)</span>
          </div>
        </div>
      </div>

      {/* Chart */}
      {data.length === 0 ? (
        <div className="flex-1 min-h-[300px] flex items-center justify-center relative z-10 border border-slate-800 border-dashed rounded-lg bg-slate-900/30">
          <div className="flex flex-col items-center gap-3 text-slate-500">
            <div className="w-8 h-8 rounded-full border-4 border-slate-700 border-t-slate-400 animate-spin" />
            <p className="font-medium text-sm">Waiting for market data...</p>
            <p className="text-xs text-center max-w-[200px]">The agent will plot the equity curve once the first trade is executed.</p>
          </div>
        </div>
      ) : (
        <div className="relative z-10 flex-1 min-h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"  stopColor={color} stopOpacity={0.2} />
                  <stop offset="100%" stopColor={color} stopOpacity={0}    />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis dataKey="ts" tick={{ fill: "#64748b", fontSize: 11 }}
                tickLine={false} axisLine={false} interval="preserveStartEnd" tickMargin={12} />
              <YAxis tickFormatter={(v) => `$${(v / 1000).toFixed(0)}K`}
                tick={{ fill: "#64748b", fontSize: 11, fontFamily: "var(--font-mono)" }} tickLine={false} axisLine={false} tickMargin={12} />
              <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#334155', strokeWidth: 1, strokeDasharray: '4 4' }} />
              <Area
                type="monotone" dataKey="equity" name="Portfolio"
                stroke={color} strokeWidth={2.5}
                fill="url(#equityGrad)" dot={false} activeDot={{ r: 5, fill: color, stroke: "#0f172a", strokeWidth: 2 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}


