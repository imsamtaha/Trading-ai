# ATLAS Subscriber Launch

ATLAS is launched as a read-only intelligence dashboard by default. Live MT5
execution remains disabled until it separately passes documented risk gates.

## Safety defaults

- `ATLAS_LIVE_TRADING=false`
- `ATLAS_DASHBOARD_ONLY=true`
- The public dashboard contains no MT5 credentials or order controls.
- The Wall Street board labels provider data as delayed until a data licence
  explicitly grants real-time display rights.
- Billing webhooks are signature-verified and auditable in Supabase.

## Commercial plans

| Plan | Price | Trial | Includes |
| --- | ---: | ---: | --- |
| ATLAS Reader | $49/month | 3 days | Read-only MT5 cockpit, Wall Street board, financial news, demo reports |
| ATLAS Trader | $99/month | 3 days | Reader plus demo MT5 connector, advanced risk reports, live-execution eligibility after approval |

The payment provider hosts Checkout. ATLAS never receives card data.

## Required production settings

Set these only in the private deployment environment:

```text
ATLAS_FINNHUB_API_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
ATLAS_STRIPE_PRICE_READER=
ATLAS_STRIPE_PRICE_TRADER=
ATLAS_APP_URL=https://your-domain.example
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
```

Create one Stripe Product and recurring monthly Price for each plan. The
application creates subscription Checkout Sessions with a three-day trial and
does not force payment method types. Configure the Stripe webhook endpoint as:

```text
https://your-domain.example/billing/stripe/webhook
```

Do not enable automatic tax until the business has the required tax
registrations. Do not activate Stripe live mode until the legal business entity
is eligible for the selected payment provider.

## Windows demo launch

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_atlas_public.ps1
```

After the local health check succeeds, validate:

```text
/subscribe
/dashboard
/dashboard/markets
/mt5/cockpit-state
```

## Execution readiness

Twenty to thirty demo executions validate wiring only. Keep
`ATLAS_LIVE_TRADING=false` until the risk review confirms order reconciliation,
daily-loss stops, a working kill switch, and a sufficiently broad forward-test
record across different market conditions.
