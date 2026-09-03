// lib/supabase.ts — Supabase client + Realtime hooks for the dashboard
import { createClient } from "@supabase/supabase-js";

const supabaseUrl  = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient(supabaseUrl, supabaseAnon);

// ── Types ──────────────────────────────────────────────────────────────────────

export interface LiveQuote {
  symbol:     string;
  ts:         string;
  price:      number;
  change_pct: number;
  volume:     number;
  regime:     "TREND_UP" | "TREND_DOWN" | "RANGE" | "BREAKOUT" | "FLAT";
}

export interface EquityPoint {
  ts:              string;
  cash:            number;
  portfolio: number;
  total:    number;
}

export interface Trade {
  id: string;
  symbol: string;
  ts: string;
  price: number;
  qty: number;
  side: string;
  strategy: string;
  pnl: number;
}

export interface Position {
  symbol:      string;
  entry_ts:    string;
  entry_price: number;
  qty:         number;
  strategy:    string;
}

export interface ModelVersion {
  version:    string;
  trained_at: string;
  val_sharpe: number;
  notes:      string;
}

export interface TradingSignal {
  id: string;
  symbol: string;
  regime: string;
  strategy: string;
  raw_signal: string;
  reason: string;
  model_version: string;
  ts: string;
}

// ── Fetchers ───────────────────────────────────────────────────────────────────

export async function fetchSignals(limit = 100): Promise<TradingSignal[]> {
  const { data } = await supabase
    .from("crypto_signals")
    .select("*")
    .order("ts", { ascending: false })
    .limit(limit);
  return (data ?? []) as TradingSignal[];
}

export async function fetchLiveQuotes(): Promise<LiveQuote[]> {
  const { data } = await supabase
    .from("crypto_live_quotes")
    .select("*")
    .order("symbol");
  return (data ?? []) as LiveQuote[];
}

export async function fetchEquityCurve(limit = 500): Promise<EquityPoint[]> {
  const { data } = await supabase
    .from("crypto_equity_curve")
    .select("*")
    .order("ts", { ascending: false })
    .limit(limit);
  return ((data ?? []) as EquityPoint[]).reverse();
}

export async function fetchTrades(limit = 100): Promise<Trade[]> {
  const { data } = await supabase
    .from("crypto_trades")
    .select("*")
    .order("ts", { ascending: false })
    .limit(limit);
  return (data ?? []) as Trade[];
}

export async function fetchLatestModelVersion(): Promise<ModelVersion | null> {
  const { data } = await supabase
    .from("model_versions")
    .select("*")
    .order("trained_at", { ascending: false })
    .limit(1);
  return data?.[0] ?? null;
}

// ── Realtime subscription helpers ─────────────────────────────────────────────

let currentQuotes: LiveQuote[] = [];

export function subscribeToLiveQuotes(
  onUpdate: (quotes: LiveQuote[]) => void
) {
  // Initial fetch
  fetchLiveQuotes().then((quotes) => {
    currentQuotes = quotes;
    onUpdate(currentQuotes);
  });

  // Subscribe to changes on live_quotes table
  const channel = supabase
    .channel(`live_quotes_changes_${Math.random()}`)
    .on(
      "postgres_changes",
      { event: "*", schema: "public", table: "crypto_live_quotes" },
      (payload) => {
        if (payload.new && Object.keys(payload.new).length > 0) {
          const newQuote = payload.new as LiveQuote;
          const idx = currentQuotes.findIndex(q => q.symbol === newQuote.symbol);
          if (idx >= 0) {
            currentQuotes[idx] = newQuote;
          } else {
            currentQuotes.push(newQuote);
          }
          onUpdate([...currentQuotes]);
        } else {
          fetchLiveQuotes().then((quotes) => {
            currentQuotes = quotes;
            onUpdate(currentQuotes);
          });
        }
      }
    )
    .subscribe();

  return () => { supabase.removeChannel(channel); };
}

export function subscribeToEquity(
  onUpdate: (point: EquityPoint) => void
) {
  const channel = supabase
    .channel(`equity_changes_${Math.random()}`)
    .on(
      "postgres_changes",
      { event: "INSERT", schema: "public", table: "crypto_equity_curve" },
      (payload) => onUpdate(payload.new as EquityPoint)
    )
    .subscribe();

  return () => { supabase.removeChannel(channel); };
}
