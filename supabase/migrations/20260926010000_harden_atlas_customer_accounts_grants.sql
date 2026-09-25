revoke all on table public.atlas_customer_accounts from public, anon, authenticated, service_role;
grant select, insert, update, delete on table public.atlas_customer_accounts to service_role;
