create table if not exists public.profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  email text,
  display_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.user_settings (
  user_id uuid primary key references auth.users(id) on delete cascade,
  language text not null default 'en',
  theme text not null default 'dark',
  updated_at timestamptz not null default now()
);

create table if not exists public.subscriptions (
  user_id uuid primary key references auth.users(id) on delete cascade,
  plan text not null default 'FREE' check (plan in ('FREE','STARTER','PRO','ELITE')),
  status text not null default 'ACTIVE',
  billing_reference text,
  updated_at timestamptz not null default now()
);

create table if not exists public.mt5_demo_connections (
  user_id uuid primary key references auth.users(id) on delete cascade,
  account_masked text not null,
  server text not null,
  broker text,
  connection_state text not null default 'DISCONNECTED',
  updated_at timestamptz not null default now()
);

create table if not exists public.demo_positions (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  symbol text not null,
  side text not null,
  entry numeric,
  simulated_pnl numeric,
  opened_at timestamptz not null default now(),
  closed_at timestamptz
);

create table if not exists public.demo_executive_events (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  symbol text,
  decision text not null,
  reason text,
  context jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;
alter table public.user_settings enable row level security;
alter table public.subscriptions enable row level security;
alter table public.mt5_demo_connections enable row level security;
alter table public.demo_positions enable row level security;
alter table public.demo_executive_events enable row level security;

create policy profiles_owner_all on public.profiles
for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy user_settings_owner_all on public.user_settings
for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy subscriptions_owner_all on public.subscriptions
for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy mt5_demo_connections_owner_all on public.mt5_demo_connections
for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy demo_positions_owner_all on public.demo_positions
for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy demo_executive_events_owner_all on public.demo_executive_events
for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
