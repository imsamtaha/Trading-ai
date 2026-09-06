begin;

create index if not exists atlas_execution_events_connection_id_idx
  on public.atlas_execution_events(connection_id);
create index if not exists billing_events_plan_id_idx
  on public.billing_events(plan_id);
create index if not exists billing_events_user_id_idx
  on public.billing_events(user_id);

do $$
begin
  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'billing_events'
      and policyname = 'Internal billing audit only'
  ) then
    create policy "Internal billing audit only"
      on public.billing_events
      for all
      to authenticated
      using (false)
      with check (false);
  end if;

  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'atlas_mt5_connections'
      and policyname = 'Internal MT5 audit only'
  ) then
    create policy "Internal MT5 audit only"
      on public.atlas_mt5_connections
      for all
      to authenticated
      using (false)
      with check (false);
  end if;

  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'atlas_execution_events'
      and policyname = 'Internal execution audit only'
  ) then
    create policy "Internal execution audit only"
      on public.atlas_execution_events
      for all
      to authenticated
      using (false)
      with check (false);
  end if;
end $$;

commit;
