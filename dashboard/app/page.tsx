// app/page.tsx — Overview page: equity curve + regime grid
import EquityCurve from "@/components/EquityCurve";
import RegimeGrid  from "@/components/RegimeGrid";
import { Activity, ShieldCheck, Zap } from "lucide-react";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Overview · AlgoPaper",
};

export default function OverviewPage() {
  return (
    <div className="space-y-8">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-white/5 pb-6">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-3">
            <Activity className="w-8 h-8 text-emerald-400" />
            Command Center
          </h1>
          <p className="text-slate-400 text-sm mt-2">
            Live paper portfolio performance and AI-predicted market regimes
          </p>
        </div>
        <div className="flex gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/20 rounded-full text-emerald-400 text-xs font-semibold tracking-wide">
            <ShieldCheck className="w-4 h-4" />
            SYSTEM SECURE
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-500/10 border border-blue-500/20 rounded-full text-blue-400 text-xs font-semibold tracking-wide">
            <Zap className="w-4 h-4" />
            AUTO TRADING
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3 flex flex-col min-h-[400px]">
          <EquityCurve />
        </div>
        <div className="lg:col-span-1 flex flex-col">
          <RegimeGrid />
        </div>
      </div>
    </div>
  );
}
