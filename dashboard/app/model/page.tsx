// app/model/page.tsx — Model version info page
import { createClient } from "@supabase/supabase-js";
import { Brain, Cpu, Database, Activity, Network, Clock } from "lucide-react";

export const dynamic = "force-dynamic";

export const metadata  = { title: "Model · AlgoPaper" };
export const revalidate = 300; // revalidate every 5 min

async function getModelInfo() {
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
  const { data } = await supabase
    .from("model_versions")
    .select("*")
    .order("trained_at", { ascending: false })
    .limit(10);
  return data ?? [];
}

function StatCard({ label, value, sub, icon: Icon, color }: { label: string; value: string; sub?: string, icon: any, color: string }) {
  return (
    <div className="rounded-2xl border border-white/5 bg-slate-900/60 backdrop-blur p-5 relative overflow-hidden group">
      {/* Decorative background glow */}
      <div className={`absolute -right-4 -top-4 w-24 h-24 blur-3xl opacity-20 transition-opacity group-hover:opacity-30 ${color}`} />
      
      <div className="flex items-start justify-between mb-2">
        <p className="text-slate-400 text-xs font-semibold uppercase tracking-wider">{label}</p>
        <Icon className={`w-4 h-4 ${color.replace('bg-', 'text-')}`} />
      </div>
      <p className="text-2xl font-bold text-white font-mono mt-1">{value}</p>
      {sub && <p className="text-slate-500 text-xs mt-2 font-medium">{sub}</p>}
    </div>
  );
}

export default async function ModelPage() {
  const versions = await getModelInfo();
  const latest   = versions[0];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-white/5 pb-6">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-3">
            <Brain className="w-8 h-8 text-violet-500" />
            Machine Learning Model
          </h1>
          <p className="text-slate-400 text-sm mt-2">
            Regime classification architecture — XGBoost, retrained weekly
          </p>
        </div>
      </div>

      {/* Latest version stats */}
      {latest ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard 
            label="Current Version"   
            value={latest.version} 
            icon={Cpu}
            color="bg-violet-500"
          />
          <StatCard 
            label="Validation Sharpe" 
            value={Number(latest.val_sharpe).toFixed(3)} 
            sub="annualised, held-out period" 
            icon={Activity}
            color={Number(latest.val_sharpe) >= 0 ? "bg-emerald-500" : "bg-rose-500"}
          />
          <StatCard
            label="Last Trained"
            value={new Date(latest.trained_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
            sub={new Date(latest.trained_at).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }) + " UTC"}
            icon={Clock}
            color="bg-blue-500"
          />
          <StatCard 
            label="Algorithm"         
            value="XGBoost"          
            sub="Gradient-boosted trees" 
            icon={Network}
            color="bg-amber-500"
          />
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-white/10 bg-slate-900/30 p-8 text-center text-slate-500 flex flex-col items-center justify-center space-y-4">
          <Database className="w-8 h-8 opacity-50" />
          <p className="text-sm">No model trained yet. Run <code className="text-slate-300 bg-slate-800 px-1.5 py-0.5 rounded font-mono">python -m agent.model.train</code> to train the first model.</p>
        </div>
      )}

      {/* Model details */}
      <div className="rounded-2xl border border-white/5 bg-slate-900/60 backdrop-blur p-6 lg:p-8 space-y-8">
        <div className="grid lg:grid-cols-2 gap-10">
          
          {/* Regime Classes */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-widest flex items-center gap-2">
              <Activity className="w-4 h-4" />
              Target Classes
            </h3>
            <div className="grid grid-cols-2 gap-3">
              {[
                { name: "TREND_UP", color: "bg-emerald-500" },
                { name: "TREND_DOWN", color: "bg-rose-500" },
                { name: "RANGE", color: "bg-amber-500" },
                { name: "BREAKOUT", color: "bg-blue-500" },
                { name: "FLAT", color: "bg-slate-500" },
              ].map((r) => (
                <div key={r.name} className="flex items-center gap-3 bg-slate-950/50 border border-white/5 p-3 rounded-xl">
                  <span className={`w-2 h-2 rounded-full ${r.color} shadow-[0_0_8px_currentColor]`} />
                  <span className="text-slate-300 font-mono text-xs font-semibold tracking-wide">{r.name}</span>
                </div>
              ))}
            </div>
          </div>
          
          {/* Key Features */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-widest flex items-center gap-2">
              <Database className="w-4 h-4" />
              Key Features <span className="px-2 py-0.5 bg-slate-800 rounded text-[10px]">28 TOTAL</span>
            </h3>
            <div className="grid sm:grid-cols-2 gap-3">
              {[
                "Returns: 1/5/10/20 bar", 
                "RSI(14), ATR(14), ADX(14)", 
                "Bollinger bandwidth", 
                "Donchian channel", 
                "Volume surge ratio", 
                "VIX level & ROC", 
                "EMA cross (9/21)", 
                "Time-of-day flags"
              ].map((f) => (
                <div key={f} className="flex items-center gap-3 bg-slate-950/50 border border-white/5 p-3 rounded-xl">
                  <div className="w-6 h-6 rounded bg-violet-500/10 flex items-center justify-center flex-shrink-0">
                    <span className="w-1.5 h-1.5 rounded-full bg-violet-400" />
                  </div>
                  <span className="text-slate-300 text-xs font-medium leading-tight">{f}</span>
                </div>
              ))}
            </div>
          </div>
          
        </div>
      </div>

      {/* Version history */}
      {versions.length > 0 && (
        <div className="rounded-2xl border border-white/5 bg-slate-900/60 backdrop-blur p-6 space-y-4">
          <h2 className="text-lg font-semibold text-white">Version History</h2>
          <div className="overflow-x-auto rounded-xl border border-white/5 bg-slate-950/20">
            <table className="w-full text-sm text-left">
              <thead className="bg-slate-900/80 border-b border-white/5 text-slate-400">
                <tr>
                  <th className="px-4 py-3 font-medium">Version</th>
                  <th className="px-4 py-3 font-medium text-right">Val Sharpe</th>
                  <th className="px-4 py-3 font-medium">Trained At</th>
                  <th className="px-4 py-3 font-medium">Notes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-slate-300">
                {versions.map((v: any, i: number) => (
                  <tr key={v.version} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-4 py-3 font-mono text-xs">
                      <div className="flex items-center gap-2">
                        {v.version}
                        {i === 0 && <span className="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">latest</span>}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-xs">
                      <span className={Number(v.val_sharpe) >= 0 ? "text-emerald-400" : "text-rose-400"}>
                        {Number(v.val_sharpe).toFixed(3)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-400 text-xs">
                      {new Date(v.trained_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}
                    </td>
                    <td className="px-4 py-3 text-slate-500 text-xs">{v.notes || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
