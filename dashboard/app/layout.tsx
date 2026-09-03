import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import MarketWatch from "@/components/MarketWatch";
import Nav from "@/components/Nav";

const inter = Inter({ subsets: ["latin"], variable: '--font-sans' });
const jbMono = JetBrains_Mono({ subsets: ["latin"], variable: '--font-mono' });

export const metadata: Metadata = {
  title: "AlgoPaper — Live Paper Trading Dashboard",
  description: "Regime-aware ML paper trading agent with live market watch, equity curve, and trade log.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`dark ${inter.variable} ${jbMono.variable}`}>
      <body className="bg-slate-950 text-slate-200 font-sans min-h-screen relative overflow-x-hidden selection:bg-blue-500/30 selection:text-white">
        
        <div className="relative z-10 flex flex-col min-h-screen">
          {/* Top nav */}
          <header className="sticky top-0 z-50 border-b border-slate-800 bg-slate-950/80 backdrop-blur-md">
            <div className="max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8 py-3 sm:py-0 sm:h-16 flex flex-col sm:flex-row sm:items-center justify-between gap-4 sm:gap-6">
              
              {/* Top Row (Mobile) / Left Side (Desktop) */}
              <div className="flex items-center justify-between w-full sm:w-auto shrink-0">
                {/* Logo */}
                <div className="flex items-center gap-3">
                  <span className="text-xl font-bold tracking-tight text-white">
                    Algo<span className="text-blue-500">Paper</span>
                  </span>
                  <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300 text-[10px] font-medium tracking-wide uppercase font-mono">
                    Live Demo
                  </span>
                </div>

                {/* Live indicator (Mobile only) */}
                <div className="sm:hidden flex items-center gap-2 text-[11px] font-medium text-white px-2.5 py-1.5 rounded-full border border-slate-700 bg-slate-800/50">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_#10b981]" />
                  System Online
                </div>
              </div>

              {/* Nav */}
              <Nav />

              {/* Live indicator (Desktop only) */}
              <div className="hidden sm:flex items-center gap-2 text-[11px] font-medium text-white px-3 py-1.5 rounded-full border border-slate-700 bg-slate-800/50 shrink-0 uppercase tracking-wider">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_#10b981]" />
                System Online
              </div>
            </div>

            {/* Market Watch bar */}
            <div className="border-t border-slate-800 bg-slate-900/50">
              <MarketWatch />
            </div>
          </header>

          {/* Page content */}
          <main className="flex-1 max-w-screen-2xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-10">
            {children}
          </main>

          {/* Footer */}
          <footer className="border-t border-slate-800 mt-auto py-8 px-4 text-center text-xs font-medium text-slate-500">
            AlgoPaper — Paper Trading AI Agent // Built with Next.js & Supabase
          </footer>
        </div>
      </body>
    </html>
  );
}
