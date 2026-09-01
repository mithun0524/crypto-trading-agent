-- CryptoPaper tables (prefixed with crypto_ to share the same Supabase project)
-- These are 100% separate from the equities tables (bars, signals, trades, etc.)

create table if not exists crypto_bars (
  id          bigserial primary key,
  symbol      text        not null,
  ts          timestamptz not null,
  open        numeric     not null,
  high        numeric     not null,
  low         numeric     not null,
  close       numeric     not null,
  volume      numeric     default 0,
  created_at  timestamptz default now(),
  unique(symbol, ts)
);

create table if not exists crypto_signals (
  id          bigserial primary key,
  symbol      text        not null,
  ts          timestamptz not null,
  regime      text        not null,
  strategy    text        not null,
  action      text        not null,
  reason      text        default '',
  model_ver   text        default 'v1',
  created_at  timestamptz default now(),
  unique(symbol, ts)
);

create table if not exists crypto_trades (
  id          bigserial primary key,
  symbol      text        not null,
  ts          timestamptz not null,
  side        text        not null,
  qty         numeric     not null,
  price       numeric     not null,
  pnl         numeric     default 0,
  strategy    text        default '',
  model_ver   text        default 'v1',
  created_at  timestamptz default now()
);

create table if not exists crypto_equity_curve (
  id          bigserial primary key,
  ts          timestamptz not null unique,
  cash        numeric     not null,
  portfolio   numeric     not null,
  total       numeric     not null,
  created_at  timestamptz default now()
);

create table if not exists crypto_live_quotes (
  id          bigserial primary key,
  symbol      text        not null unique,
  price       numeric     not null,
  change_pct  numeric     default 0,
  volume      bigint      default 0,
  regime      text        default 'FLAT',
  updated_at  timestamptz default now()
);

-- Enable Realtime for live dashboard updates
alter publication supabase_realtime add table crypto_live_quotes;
alter publication supabase_realtime add table crypto_equity_curve;
alter publication supabase_realtime add table crypto_signals;
