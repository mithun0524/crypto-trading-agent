// app/positions/page.tsx — Open positions page
import PositionsTable from "@/components/PositionsTable";
import { createClient } from "@supabase/supabase-js";

export const dynamic = "force-dynamic";

export const metadata = { title: "Positions · AlgoPaper" };
export const revalidate = 30; // ISR: revalidate every 30s

async function getOpenPositions() {
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
  // Open positions are derived from trades that have entry_ts but no exit_ts
  const { data } = await supabase
    .from("trades")
    .select("symbol, entry_ts, entry_price, qty, strategy")
    .is("exit_ts", null)
    .order("entry_ts", { ascending: false });
  return data ?? [];
}

export default async function PositionsPage() {
  const positions = await getOpenPositions();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Open Positions</h1>
        <p className="text-slate-400 text-sm mt-1">
          Live unrealized P&L, updated every bar from Supabase Realtime
        </p>
      </div>
      <PositionsTable positions={positions as any} />
    </div>
  );
}
