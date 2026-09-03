// app/page.tsx — Overview page: equity curve + regime grid
import EquityCurve from "@/components/EquityCurve";
import RegimeGrid  from "@/components/RegimeGrid";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Overview · AlgoPaper",
};

export default function OverviewPage() {
  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Page title */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">Overview</h1>
        <p className="text-slate-400 text-xs sm:text-sm mt-1 sm:mt-1.5">
          Live paper portfolio performance and AI-predicted market regimes
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        <div className="lg:col-span-2 flex flex-col">
          <EquityCurve />
        </div>
        <div className="lg:col-span-1 flex flex-col">
          <RegimeGrid />
        </div>
      </div>
    </div>
  );
}
