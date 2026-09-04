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
  
  const { data } = await supabase
    .from("crypto_trades")
    .select("*")
    .order("ts", { ascending: true });
    
  if (!data) return [];
  
  // Compute open positions by aggregating trades
  const positionsMap: Record<string, any> = {};
  
  for (const trade of data) {
    const sym = trade.symbol;
    if (!positionsMap[sym]) {
      positionsMap[sym] = { symbol: sym, qty: 0, entry_price: 0, strategy: trade.strategy, entry_ts: trade.ts };
    }
    
    const isBuy = trade.side === "BUY" || trade.side === "LONG";
    const tradeQty = isBuy ? trade.qty : -trade.qty;
    const currentQty = positionsMap[sym].qty;
    
    // Simple average price logic for simplicity
    if (Math.sign(currentQty + tradeQty) !== Math.sign(currentQty) && currentQty !== 0) {
      // Position flipped or closed
      positionsMap[sym].entry_price = trade.price;
      positionsMap[sym].entry_ts = trade.ts;
    } else if (currentQty === 0) {
      // New position
      positionsMap[sym].entry_price = trade.price;
      positionsMap[sym].entry_ts = trade.ts;
    } else {
      // Averaging down/up (approximate)
      positionsMap[sym].entry_price = (positionsMap[sym].entry_price * Math.abs(currentQty) + trade.price * Math.abs(tradeQty)) / (Math.abs(currentQty) + Math.abs(tradeQty));
    }
    
    positionsMap[sym].qty += tradeQty;
    positionsMap[sym].strategy = trade.strategy;
  }
  
  // Filter out closed positions (qty == 0, with small float tolerance)
  return Object.values(positionsMap)
    .filter(p => Math.abs(p.qty) > 0.0001)
    .sort((a, b) => new Date(b.entry_ts).getTime() - new Date(a.entry_ts).getTime());
}

export default async function PositionsPage() {
  const positions = await getOpenPositions();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Open Positions</h1>
        <p className="text-slate-400 text-sm mt-1">
          Live unrealized P&L, derived from trades and updated via Realtime
        </p>
      </div>
      <PositionsTable positions={positions as any} />
    </div>
  );
}
