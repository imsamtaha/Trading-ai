alter table public.atlas_execution_events enable row level security;
alter table public.atlas_mt5_connections enable row level security;

drop policy if exists "Enable read access for all users" on public.atlas_execution_events;
drop policy if exists "Enable read access for all users" on public.atlas_mt5_connections;

revoke all on table public.atlas_execution_events from public, anon, authenticated, service_role;
revoke all on table public.atlas_mt5_connections from public, anon, authenticated, service_role;

grant select, insert, update, delete on table public.atlas_execution_events to service_role;
grant select, insert, update, delete on table public.atlas_mt5_connections to service_role;
