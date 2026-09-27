create index if not exists atlas_user_demo_positions_user_id_idx
on public.atlas_user_demo_positions(user_id);

create index if not exists atlas_user_demo_executive_events_user_id_idx
on public.atlas_user_demo_executive_events(user_id);

drop policy if exists atlas_user_profiles_owner_all on public.atlas_user_profiles;
create policy atlas_user_profiles_owner_all on public.atlas_user_profiles
for all using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists atlas_user_settings_owner_all on public.atlas_user_settings;
create policy atlas_user_settings_owner_all on public.atlas_user_settings
for all using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists atlas_user_subscriptions_owner_all on public.atlas_user_subscriptions;
create policy atlas_user_subscriptions_owner_all on public.atlas_user_subscriptions
for all using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists atlas_user_mt5_demo_connections_owner_all on public.atlas_user_mt5_demo_connections;
create policy atlas_user_mt5_demo_connections_owner_all on public.atlas_user_mt5_demo_connections
for all using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists atlas_user_demo_positions_owner_all on public.atlas_user_demo_positions;
create policy atlas_user_demo_positions_owner_all on public.atlas_user_demo_positions
for all using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists atlas_user_demo_executive_events_owner_all on public.atlas_user_demo_executive_events;
create policy atlas_user_demo_executive_events_owner_all on public.atlas_user_demo_executive_events
for all using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);
