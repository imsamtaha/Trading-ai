# ATLAS Unified Setup

Included in the application:
- MT5 read-only telemetry and the protected execution gate
- Multi-timeframe analysis for 5m, 15m, 30m, and 1h
- Subscriber dashboard, Wall Street board, and financial-news context
- Stripe Checkout plans: ATLAS Reader at 49 USD/month and ATLAS Pro Reader at 99 USD/month, each with a 3-day trial
- Signed Stripe webhook events recorded in existing private Supabase billing tables
- GitHub Actions tests

Before enabling billing:
1. Apply the existing Supabase migrations in sequence.
2. Create two separate Stripe monthly recurring Prices.
3. Put their Price IDs in ATLAS_STRIPE_PRICE_READER and ATLAS_STRIPE_PRICE_PRO.
4. Set a restricted Stripe key in STRIPE_RESTRICTED_KEY.
5. Create a Stripe webhook for POST /billing/webhook and set STRIPE_WEBHOOK_SECRET.
6. Deploy to a stable HTTPS URL and set ATLAS_APP_URL.

Safety:
- Market board and news are human context only. They do not enter the execution engine.
- Subscriber plans are observational and cannot control MT5.
- Stripe webhook signatures are checked against the raw request body.
- Keep ATLAS_LIVE_TRADING=false through a pre-defined demo forward-test plan.
