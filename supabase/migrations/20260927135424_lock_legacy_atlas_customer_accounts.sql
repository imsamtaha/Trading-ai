create policy atlas_customer_accounts_deny_authenticated on public.atlas_customer_accounts for all to authenticated using (false) with check (false);
