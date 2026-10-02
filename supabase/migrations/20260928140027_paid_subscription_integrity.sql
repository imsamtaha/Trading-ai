alter table public.atlas_user_subscriptions add column if not exists expires_at timestamptz;
alter table public.atlas_user_subscriptions enable row level security;
revoke all on table public.atlas_user_subscriptions from anon, authenticated;
grant select on table public.atlas_user_subscriptions to authenticated;
drop policy if exists atlas_user_subscriptions_owner_all on public.atlas_user_subscriptions;
drop policy if exists atlas_user_subscriptions_owner_select on public.atlas_user_subscriptions;
create policy atlas_user_subscriptions_owner_select on public.atlas_user_subscriptions for select to authenticated using ((select auth.uid()) = user_id);
grant select, insert, update, delete on table public.atlas_user_subscriptions to service_role;
