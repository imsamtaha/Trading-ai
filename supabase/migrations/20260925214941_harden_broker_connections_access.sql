alter table public.broker_connections enable row level security;
drop policy if exists "Enable read access for all users" on public.broker_connections;
revoke all on table public.broker_connections from public, anon, authenticated, service_role;
grant select, insert, update, delete on table public.broker_connections to authenticated, service_role;
