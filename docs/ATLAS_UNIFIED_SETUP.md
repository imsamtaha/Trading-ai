# ATLAS Unified Setup

Included in the application:

- MT5 read-only telemetry and the protected execution gate
- Multi-timeframe analysis for 5m, 15m, 30m, and 1h
- Subscriber dashboard, Wall Street board, and financial-news context
- Whish Money request plans: ATLAS Reader at 49 USD/month and ATLAS Pro Reader
  at 99 USD/month, each with a 3-day trial arranged after manual approval
- Private local audit records for Whish payment requests
- GitHub Actions tests

Before enabling payment requests:

1. Verify the receiving Whish wallet and customer-support number.
2. Set `ATLAS_WHISH_ENABLED=true`, `ATLAS_WHISH_RECIPIENT`, and
   `ATLAS_WHISH_SUPPORT` in the private environment.
3. Set a private, backed-up `ATLAS_WHISH_DB` location.
4. Deploy to a stable HTTPS URL and set `ATLAS_APP_URL`.
5. Protect `/dashboard*` with Cloudflare Access and manually add only
   reconciled subscriber emails.

Safety:

- Whish requests are not payment confirmation and never activate access automatically.
- Market board and news are human context only. They do not enter the execution engine.
- Subscriber plans are observational and cannot control MT5.
- Keep `ATLAS_LIVE_TRADING=false` through a pre-defined demo forward-test plan.
