"use client";
// components/EquityCurve.tsx — Live equity curve vs SPY buy-and-hold benchmark

import { useEffect, useState } from "react";
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip
} from "recharts";
import { fetchEquityCurve, subscribeToEquity, EquityPoint } from "@/lib/supabase";
import { TrendingUp, Moon } from "lucide-react";

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
      equity: p.total,
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
    const unsub = subscribeToEquity((p) => {
      setData((prev) => {
        const newData = [...prev, {
          ts:     new Date(p.ts).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }),
          equity: p.total,
          label:  p.ts,
        }];
        if (newData.length > 500) newData.shift();
        
        const latest = p.total;
        setStats({
          pnl:    latest - STARTING_EQUITY,
          pnlPct: ((latest - STARTING_EQUITY) / STARTING_EQUITY) * 100,
          latest,
        });
        
        return newData;
      });
    });
    return unsub;
  }, []);

  const isUp = stats.pnl >= 0;

  return (
    <div className="flex-1 rounded-2xl border border-white/5 bg-slate-900/60 backdrop-blur p-6 flex flex-col relative overflow-hidden">
      {/* Decorative background glow */}
      <div className={`absolute top-0 right-0 w-64 h-64 blur-3xl opacity-20 pointer-events-none rounded-full translate-x-1/2 -translate-y-1/2 ${isUp ? "bg-emerald-500" : "bg-rose-500"}`} />
      
      <div className="flex items-start justify-between mb-8 z-10">
        <div>
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-widest mb-1 flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            Total Equity
          </h2>
          <div className="flex items-baseline gap-3 mt-2">
            <p className="text-4xl font-bold tracking-tight text-white tabular-nums">
              {formatCurrency(stats.latest)}
            </p>
            <div className={`flex items-center gap-1 text-sm font-semibold px-2 py-1 rounded-md ${isUp ? "bg-emerald-500/10 text-emerald-400" : "bg-rose-500/10 text-rose-400"}`}>
              {isUp ? "+" : ""}{formatCurrency(stats.pnl)} ({formatPct(stats.latest)})
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs font-medium text-slate-500 bg-slate-950/50 px-3 py-1.5 rounded-full border border-white/5">
          <Moon className="w-3.5 h-3.5" />
          Realtime
        </div>
      </div>

      <div className="flex-1 min-h-[300px] z-10">
        {data.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-600 text-sm">
            Waiting for data points...
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={isUp ? "#10b981" : "#f43f5e"} stopOpacity={0.4}/>
                  <stop offset="95%" stopColor={isUp ? "#10b981" : "#f43f5e"} stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff0a" vertical={false} />
              <XAxis 
                dataKey="ts" 
                stroke="#ffffff40" 
                fontSize={11} 
                tickMargin={12} 
                minTickGap={40}
                axisLine={false}
                tickLine={false}
              />
              <YAxis 
                stroke="#ffffff40" 
                fontSize={11} 
                tickFormatter={(val) => `$${(val/1000).toFixed(0)}k`} 
                domain={['auto', 'auto']}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#ffffff20', strokeWidth: 1, strokeDasharray: '4 4' }} />
              <Area 
                type="monotone" 
                dataKey="equity" 
                stroke={isUp ? "#10b981" : "#f43f5e"} 
                strokeWidth={3} 
                fill="url(#colorEquity)" 
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
