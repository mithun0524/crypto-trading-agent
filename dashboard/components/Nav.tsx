"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/",           label: "Dashboard" },
  { href: "/positions",  label: "Positions" },
  { href: "/trades",     label: "Trade Log" },
  { href: "/model",      label: "AI Model" },
];

export default function Nav() {
  const path = usePathname();
  return (
    <nav
      style={{
        background: "rgba(4, 4, 15, 0.85)",
        borderBottom: "1px solid rgba(99,102,241,0.2)",
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
      }}
      className="sticky top-0 z-50"
    >
      <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-2">
          <span style={{ fontSize: "1.3rem" }}>₿</span>
          <span
            style={{
              fontFamily: "'Space Grotesk', sans-serif",
              fontWeight: 700,
              fontSize: "1.1rem",
              background: "linear-gradient(135deg, #6366F1, #A855F7, #00FFA3)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            CryptoPaper
          </span>
          <span
            style={{
              fontSize: "0.65rem",
              padding: "1px 6px",
              borderRadius: "4px",
              background: "rgba(99,102,241,0.2)",
              color: "#6366F1",
              fontWeight: 600,
              letterSpacing: "0.05em",
            }}
          >
            LIVE 24/7
          </span>
          <span className="live-dot ml-1" />
        </div>

        {/* Nav links */}
        <div className="flex items-center gap-1">
          {links.map(({ href, label }) => {
            const active = path === href;
            return (
              <Link
                key={href}
                href={href}
                style={{
                  padding: "5px 14px",
                  borderRadius: "8px",
                  fontSize: "0.85rem",
                  fontWeight: active ? 600 : 400,
                  color: active ? "#E8E8FF" : "#6B7DB3",
                  background: active ? "rgba(99,102,241,0.2)" : "transparent",
                  border: active ? "1px solid rgba(99,102,241,0.4)" : "1px solid transparent",
                  transition: "all 0.15s ease",
                  textDecoration: "none",
                }}
              >
                {label}
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
