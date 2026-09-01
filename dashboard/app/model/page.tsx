// app/model/page.tsx — Model version info page
import { createClient } from "@supabase/supabase-js";

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

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-white/5 bg-slate-900/60 p-4">
      <p className="text-slate-400 text-xs font-medium mb-1">{label}</p>
      <p className="text-xl font-bold text-white">{value}</p>
      {sub && <p className="text-slate-500 text-xs mt-0.5">{sub}</p>}
    </div>
  );
}

export default async function ModelPage() {
  const versions = await getModelInfo();
  const latest   = versions[0];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Model</h1>
        <p className="text-slate-400 text-sm mt-1">
          Regime classification model — XGBoost, retrained weekly
        </p>
      </div>

      {/* Latest version stats */}
      {latest ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <StatCard label="Current Version"   value={latest.version}   />
          <StatCard label="Validation Sharpe" value={Number(latest.val_sharpe).toFixed(3)} sub="annualised, held-out period" />
          <StatCard
            label="Last Trained"
            value={new Date(latest.trained_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
            sub={new Date(latest.trained_at).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }) + " UTC"}
          />
          <StatCard label="Algorithm"         value="XGBoost"          sub="Gradient-boosted trees, deterministic" />
        </div>
      ) : (
        <div className="rounded-xl border border-white/5 bg-slate-900/60 p-6 text-slate-500 text-sm">
          No model trained yet. Run <code className="text-slate-300">python -m agent.model.train</code> to train the first model.
        </div>
      )}

      {/* Model details */}
      <div className="rounded-2xl border border-white/5 bg-slate-900/60 backdrop-blur p-6 space-y-4">
        <h2 className="text-lg font-semibold text-white">Model Details</h2>
        <div className="grid sm:grid-cols-2 gap-6 text-sm">
          <div className="space-y-2">
            <h3 className="text-slate-300 font-medium">Regime Classes</h3>
            {["TREND_UP", "TREND_DOWN", "RANGE", "BREAKOUT", "FLAT"].map((r) => (
              <div key={r} className="flex items-center gap-2 text-slate-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                {r}
              </div>
            ))}
          </div>
          <div className="space-y-2">
            <h3 className="text-slate-300 font-medium">Key Features (28 total)</h3>
            {["Returns: 1/5/10/20 bar", "RSI(14), ATR(14), ADX(14)", "Bollinger bandwidth & position", "Donchian channel position", "Volume surge ratio", "VIX level & rate of change", "EMA cross (9/21)", "Time-of-day flags"].map((f) => (
              <div key={f} className="flex items-center gap-2 text-slate-400">
                <span className="w-1.5 h-1.5 rounded-full bg-violet-400" />
                {f}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Version history */}
      {versions.length > 1 && (
        <div className="rounded-2xl border border-white/5 bg-slate-900/60 backdrop-blur p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Version History</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-500 border-b border-white/5">
                  <th className="text-left pb-3 font-medium">Version</th>
                  <th className="text-right pb-3 font-medium">Val Sharpe</th>
                  <th className="text-left pb-3 font-medium pl-4">Trained</th>
                  <th className="text-left pb-3 font-medium pl-4">Notes</th>
                </tr>
              </thead>
              <tbody>
                {versions.map((v: any, i: number) => (
                  <tr key={v.version} className="border-b border-white/5">
                    <td className="py-2.5 font-mono text-slate-300 text-xs">
                      {v.version}
                      {i === 0 && <span className="ml-2 px-1.5 py-0.5 rounded-full bg-emerald-400/10 text-emerald-400 text-[10px]">latest</span>}
                    </td>
                    <td className="py-2.5 text-right tabular-nums">
                      <span className={Number(v.val_sharpe) >= 0 ? "text-emerald-400" : "text-red-400"}>
                        {Number(v.val_sharpe).toFixed(3)}
                      </span>
                    </td>
                    <td className="py-2.5 pl-4 text-slate-400 text-xs">
                      {new Date(v.trained_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                    </td>
                    <td className="py-2.5 pl-4 text-slate-500 text-xs">{v.notes || "—"}</td>
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
