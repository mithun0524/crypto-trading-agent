// lib/supabase.ts – Supabase client + Realtime hooks for the crypto dashboard
import { createClient } from "@supabase/supabase-js";

const supabaseUrl  = (process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://placeholder.supabase.co');
const supabaseAnon = (process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'placeholder');

export const supabase = createClient(supabaseUrl, supabaseAnon);

// ── Types ────────────────────────────────────────────────────────────────────

export interface LiveQuote {
  symbol:     string;
  // DB columns: price, updated_at, change_pct, volume, regime
  updated_at: string;
  price:      number;
  last_price: number;   // alias – populated from price in fetchLiveQuotes()
  ts:         string;   // alias – populated from updated_at
  change_pct: number;
  volume:     number;
  regime:     string;
}

export interface EquityPoint {
  ts:              string;
  cash:            number;
  portfolio:       number;   // DB column is "portfolio"
  total:           number;   // DB column is "total"
  // Dashboard aliases
  positions_value: number;   // = portfolio
  total_equity:    number;   // = total
}

export interface Trade {
  id:          string;
  symbol:      string;
  entry_ts:    string;
  entry_price: number;
  exit_ts:     string;
  exit_price:  number;
  qty:         number;
  side:        string;
  strategy:    string;
  pnl:         number;
  commission:  number;
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

// ── Fetchers ─────────────────────────────────────────────────────────────────

export async function fetchLiveQuotes(): Promise<LiveQuote[]> {
  const { data, error } = await supabase
    .from("crypto_live_quotes")
    .select("*")
    .order("symbol");
  if (error) console.error("fetchLiveQuotes error:", error);
  // Normalise: add dashboard-expected aliases for price → last_price, updated_at → ts
  return ((data ?? []) as any[]).map((row) => ({
    ...row,
    last_price: row.price,
    ts:         row.updated_at,
  })) as LiveQuote[];
}

export async function fetchEquityCurve(limit = 500): Promise<EquityPoint[]> {
  const { data, error } = await supabase
    .from("crypto_equity_curve")
    .select("*")
    .order("ts", { ascending: false })
    .limit(limit);
  if (error) console.error("fetchEquityCurve error:", error);
  // Normalise: add aliases for total → total_equity, portfolio → positions_value
  return (((data ?? []) as any[]).map((row) => ({
    ...row,
    total_equity:    row.total,
    positions_value: row.portfolio,
  })) as EquityPoint[]).reverse();
}

export async function fetchTrades(limit = 200): Promise<Trade[]> {
  const { data, error } = await supabase
    .from("crypto_trades")
    .select("*")
    .order("ts", { ascending: false })
    .limit(limit);
  if (error) console.error("fetchTrades error:", error);
  return (data ?? []) as Trade[];
}

export async function fetchLatestModelVersion(): Promise<ModelVersion | null> {
  const { data } = await supabase
    .from("crypto_model_versions")
    .select("*")
    .order("trained_at", { ascending: false })
    .limit(1);
  return data?.[0] ?? null;
}

// ── Realtime subscription helpers ────────────────────────────────────────────

export function subscribeToLiveQuotes(
  onUpdate: (quotes: LiveQuote[]) => void
) {
  // Initial fetch
  fetchLiveQuotes().then(onUpdate);

  const channel = supabase
    .channel(`crypto_quotes_${Math.random()}`)
    .on(
      "postgres_changes",
      { event: "*", schema: "public", table: "crypto_live_quotes" },
      () => fetchLiveQuotes().then(onUpdate)
    )
    .subscribe();

  return () => { supabase.removeChannel(channel); };
}

export function subscribeToEquity(
  onUpdate: (point: EquityPoint) => void
) {
  const channel = supabase
    .channel(`crypto_equity_${Math.random()}`)
    .on(
      "postgres_changes",
      { event: "INSERT", schema: "public", table: "crypto_equity_curve" },
      (payload) => {
        const row = payload.new as any;
        onUpdate({
          ...row,
          total_equity:    row.total,
          positions_value: row.portfolio,
        } as EquityPoint);
      }
    )
    .subscribe();

  return () => { supabase.removeChannel(channel); };
}
