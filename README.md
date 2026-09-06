# ATLAS Market

The public website for ATLAS Trading AI provides a responsive introduction and
an interactive, explicitly synthetic demo. It works without accounts, API keys,
payment details, or an MT5 terminal. No browser requests reach private telemetry.
Optional Google signup is implemented through Supabase Auth, but Google provider
activation is pending. See [Google sign-in setup](docs/GOOGLE_SIGN_IN.md).

## Public website

Preview from the repository root:

```sh
python -m http.server 4173 --bind 127.0.0.1 --directory web
```

Visit `http://127.0.0.1:4173`. The private FastAPI application also serves this
website at `/`; the previous JSON service metadata is now at `/api`.
Existing `/subscribe`, `/billing/*`, and `/dashboard*` routes remain intact.

## Publish on Vercel or Netlify

Suggested project name: **atlas-market**. A provider must confirm subdomain
availability; no paid domain has been purchased or reserved.

- Vercel: import `imsamtaha/Trading-ai`, select the integration branch until it
  is merged, choose **Other**, and use the repository's `vercel.json`. No install
  or build command; output directory `web`. The `.vercelignore` allowlist excludes
  the Python application and secrets from CLI uploads.
- Netlify: import the same repository/branch. `netlify.toml` publishes `web` with
  no build command. Only the files in that directory become website assets.
- Sites: run `python scripts/build_website.py`, then package the configured
  `out` directory through the Sites publishing workflow.

The public site is a marketing and demonstration surface. It is **not** the
private Python/MT5 service. Do not deploy private broker/account endpoints as
unauthenticated public APIs. MT5 still requires its persistent Windows host.

## Validate

```sh
python -m pip install -r requirements.txt
python -m pytest -q
node --test tests/test_demo_model.cjs
python scripts/build_website.py
```

The static builder checks local links, section anchors, an exact public-file
allowlist, and private-configuration markers. API tests check that the page and
assets work in dashboard-only mode and execution routes remain blocked.

## Private service readiness

Keep `ATLAS_LIVE_TRADING=false` and `ATLAS_DASHBOARD_ONLY=true`.
See [README_MT5.md](README_MT5.md) and [ATLAS_LAUNCH.md](ATLAS_LAUNCH.md).
Subscriber authentication, licensed market-data display, payment configuration,
and webhook-to-access provisioning must be verified before selling access.
Existing paid-plan code is preserved; this public preview does not start Checkout.

## Advertising

Direct visitors to the published homepage or its `#demo` section. The website
includes a share-link button and search/social metadata. Sample copy is in
[docs/ADVERTISING.md](docs/ADVERTISING.md). No advertising campaigns, spending,
tracking pixels, return claims, or performance testimonials are configured.
