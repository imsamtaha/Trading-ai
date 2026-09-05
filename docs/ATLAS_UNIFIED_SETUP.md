# ATLAS Unified Setup

Integrated services:
- MT5 read-only telemetry and protected execution gate
- Multi-timeframe analysis for 5m, 15m, 30m, and 1h
- Subscriber dashboard, Wall Street board, and financial-news context
- Stripe Checkout plans: Reader 49 USD/month and Pro Reader 99 USD/month, each with a 3-day trial
- Signed Stripe webhook events in a private Supabase billing audit table
- GitHub Actions test workflow

Before enabling billing:
1. Apply supabase/migrations/20260905_atlas_billing.sql in Supabase.
2. Create two separate Stripe monthly recurring products and prices.
3. Set STRIPE_PRICE_READER and STRIPE_PRICE_PRO in the private environment.
4. Use a restricted Stripe API key in STRIPE_RESTRICTED_KEY.
5. Create a Stripe webhook for POST /billing/webhook and set STRIPE_WEBHOOK_SECRET.
6. Deploy the API to a stable HTTPS URL and set ATLAS_PUBLIC_BASE_URL.

Safety:
- Market board and news are human context only. They have no execution path.
- Subscriber plans are observational and cannot control MT5.
- Webhook signatures are checked against the raw request body.
- Supabase billing records use RLS and no anon or authenticated access.
- Keep ATLAS_LIVE_TRADING=false through a pre-defined demo forward-test plan.
