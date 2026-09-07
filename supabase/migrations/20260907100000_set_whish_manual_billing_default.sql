-- Stripe has been retired from ATLAS. Preserve historical records as audit data,
-- but make Whish Money manual review the only default for future commerce rows.
begin;

alter table public.subscriptions
  alter column provider set default 'whish_manual';

alter table public.billing_events
  alter column provider set default 'whish_manual';

commit;
