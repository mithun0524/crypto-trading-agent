import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";

export const metadata: Metadata = {
  title: "CryptoPaper | AI Crypto Trading Agent",
  description: "Live 24/7 AI-powered cryptocurrency paper trading dashboard. Real-time signals for BTC, ETH, SOL, DOGE.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen">
        <Nav />
        <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
