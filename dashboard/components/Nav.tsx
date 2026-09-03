"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const links = [
  { href: "/",           label: "Dashboard" },
  { href: "/positions",  label: "Positions" },
  { href: "/trades",     label: "Trade Log" },
  { href: "/reasoning",  label: "Bot Reasoning" },
  { href: "/model",      label: "AI Model" },
];

export default function Nav() {
  const path = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

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
          <span style={{ fontSize: "1.3rem" }}>?</span>
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
            className="hidden sm:inline-block"
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
          <span className="live-dot ml-1 hidden sm:inline-block" />
        </div>

        {/* Desktop Nav */}
        <div className="hidden md:flex items-center gap-1">
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

        {/* Mobile Hamburger */}
        <div className="md:hidden">
          <button 
            onClick={() => setMenuOpen(!menuOpen)}
            className="text-gray-300 hover:text-white p-2"
          >
            {menuOpen ? "?" : "?"}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {menuOpen && (
        <div className="md:hidden bg-[#04040f] border-b border-indigo-500/20 py-2 px-4 flex flex-col gap-2">
          {links.map(({ href, label }) => {
            const active = path === href;
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setMenuOpen(false)}
                className={\lock px-3 py-2 rounded-md text-sm font-medium \\}
              >
                {label}
              </Link>
            );
          })}
        </div>
      )}
    </nav>
  );
}
