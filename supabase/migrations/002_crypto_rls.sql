-- ============================================================
-- CryptoPaper – Supabase Row Level Security (RLS) Fix
-- Run this in Supabase SQL Editor (Dashboard → SQL Editor → New query)
-- ============================================================

-- The python agent auto-created the crypto tables without RLS policies.
-- Supabase blocks the anonymous frontend from reading them by default.

ALTER TABLE IF EXISTS crypto_live_quotes ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS crypto_equity_curve ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS crypto_trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS crypto_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS crypto_model_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS crypto_bars ENABLE ROW LEVEL SECURITY;

-- Allow public (anon) read on all crypto tables (dashboard is public)
DO $ $
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE policyname = 'anon read crypto_live_quotes'
  ) THEN
    CREATE POLICY "anon read crypto_live_quotes" ON crypto_live_quotes FOR SELECT USING (true);
    CREATE POLICY "anon read crypto_equity_curve" ON crypto_equity_curve FOR SELECT USING (true);
    CREATE POLICY "anon read crypto_trades" ON crypto_trades FOR SELECT USING (true);
    CREATE POLICY "anon read crypto_signals" ON crypto_signals FOR SELECT USING (true);
    CREATE POLICY "anon read crypto_model_versions" ON crypto_model_versions FOR SELECT USING (true);
    CREATE POLICY "anon read crypto_bars" ON crypto_bars FOR SELECT USING (true);
  END IF;
END
$ $;

-- Make sure Realtime is enabled for the new crypto tables
ALTER PUBLICATION supabase_realtime ADD TABLE crypto_live_quotes;
ALTER PUBLICATION supabase_realtime ADD TABLE crypto_equity_curve;
