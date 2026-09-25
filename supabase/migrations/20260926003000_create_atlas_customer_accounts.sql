create table if not exists public.atlas_customer_accounts (
  customer_id text not null,
  account_id text not null,
  auth_subject uuid not null references auth.users(id) on delete cascade,
  tier text not null check (tier in ('PRO','ELITE')),
  mode text not null default 'LIVE_DEMO' check (mode in ('LIVE_DEMO')),
  broker text not null default 'FXPRO',
  broker_login bigint,
  broker_server text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (customer_id, account_id)
);
create index if not exists atlas_customer_accounts_auth_subject_idx on public.atlas_customer_accounts(auth_subject);
alter table public.atlas_customer_accounts enable row level security;
-- No public RLS policy: backend service credentials own customer mapping writes/reads.
