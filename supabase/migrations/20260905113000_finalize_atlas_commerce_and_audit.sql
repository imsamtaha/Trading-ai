begin;

alter table public.subscription_plans
  add column if not exists trial_days integer not null default 3 check (trial_days between 0 and 31),
  add column if not exists provider_price_id text,
  add column if not exists features jsonb not null default '[]'::jsonb,
  add column if not exists display_order smallint not null default 0;

alter table public.subscriptions
  add column if not exists provider text not null default 'stripe',
  add column if not exists trial_ends_at timestamptz,
  add column if not exists cancel_at_period_end boolean not null default false;

update public.subscription_plans
set active = false
where id in ('starter', 'pro', 'elite');

insert into public.subscription_plans
  (id, name, monthly_price, trial_days, features, display_order, active)
values
  ('reader', 'ATLAS Reader', 49.00, 3,
   '["Read-only MT5 cockpit","Wall Street board","Financial news","Demo performance reports"]'::jsonb, 10, true),
  ('trader', 'ATLAS Trader', 99.00, 3,
   '["Everything in Reader","Demo MT5 connector","Advanced risk reports","Live execution eligibility after risk approval"]'::jsonb, 20, true)
on conflict (id) do update set
  name = excluded.name,
  monthly_price = excluded.monthly_price,
  trial_days = excluded.trial_days,
  features = excluded.features,
  display_order = excluded.display_order,
  active = true;

create table if not exists public.billing_events (
  id uuid primary key default gen_random_uuid(),
  provider text not null default 'stripe',
  provider_event_id text not null unique,
  event_type text not null,
  user_id uuid references auth.users(id) on delete set null,
  email text,
  plan_id text references public.subscription_plans(id) on delete set null,
  provider_customer_id text,
  provider_subscription_id text,
  status text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.atlas_mt5_connections (
  id uuid primary key default gen_random_uuid(),
  environment text not null default 'demo' check (environment in ('demo', 'paper', 'live')),
  broker text not null default 'MetaTrader 5',
  server text,
  mt5_login bigint,
  terminal_host text,
  status text not null default 'disconnected' check (status in ('connected', 'disconnected', 'error')),
  last_seen_at timestamptz,
  updated_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create table if not exists public.atlas_execution_events (
  id uuid primary key default gen_random_uuid(),
  connection_id uuid references public.atlas_mt5_connections(id) on delete set null,
  symbol text not null,
  timeframe text not null default 'MTF',
  decision text not null default 'WAIT',
  confidence numeric,
  risk_level text,
  directional_score numeric,
  status text not null default 'DRY_RUN',
  reason text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists subscriptions_plan_id_idx on public.subscriptions(plan_id);
create unique index if not exists subscriptions_provider_subscription_uidx
  on public.subscriptions(provider_subscription_id);
create index if not exists billing_events_provider_subscription_idx
  on public.billing_events(provider_subscription_id);
create index if not exists atlas_execution_events_created_at_idx
  on public.atlas_execution_events(created_at desc);
create index if not exists atlas_execution_events_status_idx
  on public.atlas_execution_events(status);

alter table public.billing_events enable row level security;
alter table public.atlas_mt5_connections enable row level security;
alter table public.atlas_execution_events enable row level security;

revoke all on table public.billing_events from anon, authenticated;
revoke all on table public.atlas_mt5_connections from anon, authenticated;
revoke all on table public.atlas_execution_events from anon, authenticated;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'trader_cockpit_state'
      and policyname = 'Users can insert own cockpit state'
  ) then
    create policy "Users can insert own cockpit state"
      on public.trader_cockpit_state
      for insert to authenticated
      with check ((select auth.uid()) = user_id);
  end if;
end $$;

commit;
