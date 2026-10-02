create table if not exists public.atlas_user_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  email text,
  display_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.atlas_user_settings (
  user_id uuid primary key references auth.users(id) on delete cascade,
  language text not null default 'en',
  theme text not null default 'dark',
  updated_at timestamptz not null default now()
);

create table if not exists public.atlas_user_subscriptions (
  user_id uuid primary key references auth.users(id) on delete cascade,
  plan text not null default 'FREE' check (plan in ('FREE','STARTER','PRO','ELITE')),
  status text not null default 'ACTIVE',
  billing_reference text,
  updated_at timestamptz not null default now()
);

create table if not exists public.atlas_user_mt5_demo_connections (
  user_id uuid primary key references auth.users(id) on delete cascade,
  account_masked text not null,
  account_type text not null default 'DEMO',
  server text not null,
  broker text,
  connection_state text not null default 'DISCONNECTED',
  updated_at timestamptz not null default now()
);

create table if not exists public.atlas_user_demo_positions (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  symbol text not null,
  side text not null,
  entry numeric,
  simulated_pnl numeric,
  opened_at timestamptz not null default now(),
  closed_at timestamptz
);

create table if not exists public.atlas_user_demo_executive_events (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  symbol text,
  decision text not null,
  reason text,
  context jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table public.atlas_user_profiles enable row level security;
alter table public.atlas_user_settings enable row level security;
alter table public.atlas_user_subscriptions enable row level security;
alter table public.atlas_user_mt5_demo_connections enable row level security;
alter table public.atlas_user_demo_positions enable row level security;
alter table public.atlas_user_demo_executive_events enable row level security;

drop policy if exists atlas_user_profiles_owner_all on public.atlas_user_profiles;
create policy atlas_user_profiles_owner_all on public.atlas_user_profiles
for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists atlas_user_settings_owner_all on public.atlas_user_settings;
create policy atlas_user_settings_owner_all on public.atlas_user_settings
for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists atlas_user_subscriptions_owner_all on public.atlas_user_subscriptions;
create policy atlas_user_subscriptions_owner_all on public.atlas_user_subscriptions
for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists atlas_user_mt5_demo_connections_owner_all on public.atlas_user_mt5_demo_connections;
create policy atlas_user_mt5_demo_connections_owner_all on public.atlas_user_mt5_demo_connections
for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists atlas_user_demo_positions_owner_all on public.atlas_user_demo_positions;
create policy atlas_user_demo_positions_owner_all on public.atlas_user_demo_positions
for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists atlas_user_demo_executive_events_owner_all on public.atlas_user_demo_executive_events;
create policy atlas_user_demo_executive_events_owner_all on public.atlas_user_demo_executive_events
for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
