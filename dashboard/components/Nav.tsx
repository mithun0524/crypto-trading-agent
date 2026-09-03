"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const NAV_ITEMS = [
  { href: "/",          label: "Overview"  },
  { href: "/positions", label: "Positions" },
  { href: "/trades",    label: "Trade Log" },
  { href: "/reasoning", label: "Bot Reasoning" },
  { href: "/model",     label: "Model"     },
];

export default function Nav() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <>
      {/* Desktop Nav */}
      <nav className="hidden sm:flex items-center gap-1 sm:mx-0 sm:px-0 sm:flex-1">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors whitespace-nowrap ${
                isActive
                  ? "text-white bg-slate-800 shadow-sm"
                  : "text-slate-400 hover:text-white hover:bg-slate-800/50"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Mobile Hamburger Button */}
      <div className="sm:hidden ml-auto">
        <button 
          onClick={() => setMenuOpen(!menuOpen)}
          className="text-slate-400 hover:text-white p-2"
        >
          {menuOpen ? "✕" : "☰"}
        </button>
      </div>

      {/* Mobile Menu Dropdown */}
      {menuOpen && (
        <div className="sm:hidden absolute top-full left-0 right-0 bg-slate-900 border-b border-slate-800 p-4 flex flex-col gap-2 shadow-xl z-50">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMenuOpen(false)}
                className={`block px-4 py-3 rounded-md text-base font-medium ${
                  isActive 
                    ? "bg-blue-500/20 text-blue-400 border border-blue-500/30" 
                    : "text-slate-300 hover:bg-slate-800"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </div>
      )}
    </>
  );
}
