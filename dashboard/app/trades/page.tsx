// app/trades/page.tsx — Trade log page
import TradeLog from "@/components/TradeLog";

export const metadata = { title: "Trade Log · AlgoPaper" };

export default function TradesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Trade Log</h1>
        <p className="text-slate-400 text-sm mt-1">
          Closed trades, per-strategy win rates, and P&L breakdown
        </p>
      </div>
      <TradeLog />
    </div>
  );
}
