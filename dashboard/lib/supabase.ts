// lib/supabase.ts — Supabase client + Realtime hooks for the dashboard
import { createClient } from "@supabase/supabase-js";

const supabaseUrl  = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient(supabaseUrl, supabaseAnon);

// ── Types ──────────────────────────────────────────────────────────────────────

export interface LiveQuote {
  symbol:     string;
  ts:         string;
  last_price: number;
  change_pct: number;
  volume:     number;
  regime:     "TREND_UP" | "TREND_DOWN" | "RANGE" | "BREAKOUT" | "FLAT";
}

export interface EquityPoint {
  ts:              string;
  cash:            number;
  positions_value: number;
  total_equity:    number;
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

export interface TradingSignal {
  id: string;
  symbol: string;
  regime: string;
  strategy: string;
  action: string;
  reason: string;
  model_version: string;
  created_at: string;
}

// ── Fetchers ───────────────────────────────────────────────────────────────────

export async function fetchSignals(limit = 100): Promise<TradingSignal[]> {
  const { data } = await supabase
    .from("signals")
    .select("*")
    .order("created_at", { ascending: false })
    .limit(limit);
  return (data ?? []) as TradingSignal[];
}

export async function fetchLiveQuotes(): Promise<LiveQuote[]> {
  const { data } = await supabase
    .from("live_quotes")
    .select("*")
    .order("symbol");
  return (data ?? []) as LiveQuote[];
}

export async function fetchEquityCurve(limit = 500): Promise<EquityPoint[]> {
  const { data } = await supabase
    .from("equity_curve")
    .select("*")
    .order("ts", { ascending: false })
    .limit(limit);
  return ((data ?? []) as EquityPoint[]).reverse();
}

export async function fetchTrades(limit = 200): Promise<Trade[]> {
  const { data } = await supabase
    .from("trades")
    .select("*")
    .order("exit_ts", { ascending: false })
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

export function subscribeToLiveQuotes(
  onUpdate: any
) {
  // Initial fetch
  fetchLiveQuotes().then(onUpdate);

  // Subscribe to changes on live_quotes table
  const channel = supabase
    .channel(`live_quotes_changes_${Math.random()}`)
    .on(
      "postgres_changes",
      { event: "*", schema: "public", table: "live_quotes" },
      (payload) => {
        if (payload.new && Object.keys(payload.new).length > 0) {
          onUpdate((prev: LiveQuote[]) => {
            const idx = prev.findIndex(q => q.symbol === (payload.new as LiveQuote).symbol);
            if (idx >= 0) {
              const updated = [...prev];
              updated[idx] = payload.new as LiveQuote;
              return updated;
            }
            return [...prev, payload.new as LiveQuote];
          });
        } else {
          fetchLiveQuotes().then(onUpdate);
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
      { event: "INSERT", schema: "public", table: "equity_curve" },
      (payload) => onUpdate(payload.new as EquityPoint)
    )
    .subscribe();

  return () => { supabase.removeChannel(channel); };
}
