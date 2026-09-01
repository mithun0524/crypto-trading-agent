import MarketWatch from "@/components/MarketWatch";
import EquityCurve from "@/components/EquityCurve";
import RegimeGrid from "@/components/RegimeGrid";

export default function Home() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1
          style={{
            fontFamily: "'Space Grotesk', sans-serif",
            fontSize: "1.6rem",
            fontWeight: 700,
            background: "linear-gradient(135deg, #E8E8FF 0%, #A855F7 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            marginBottom: "4px",
          }}
        >
          Crypto Trading Dashboard
        </h1>
        <p style={{ color: "#6B7DB3", fontSize: "0.875rem" }}>
          AI-powered paper trading · BTC · ETH · SOL · DOGE · 24/7 live
        </p>
      </div>

      {/* Live Crypto Prices */}
      <MarketWatch />

      {/* Equity Curve */}
      <div>
        <h2
          style={{
            fontFamily: "'Space Grotesk', sans-serif",
            fontWeight: 600,
            fontSize: "1rem",
            color: "#E8E8FF",
            marginBottom: "12px",
          }}
        >
          Portfolio Performance
        </h2>
        <EquityCurve />
      </div>

      {/* Regime signals */}
      <div>
        <h2
          style={{
            fontFamily: "'Space Grotesk', sans-serif",
            fontWeight: 600,
            fontSize: "1rem",
            color: "#E8E8FF",
            marginBottom: "12px",
          }}
        >
          AI Regime Signals
        </h2>
        <RegimeGrid />
      </div>
    </div>
  );
}
