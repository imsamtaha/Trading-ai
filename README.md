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

## Deploy to Google Cloud Run

The repository includes a safety-locked Cloud Run container, build-only Cloud
Build pipeline, and a staged PowerShell deployment script. A candidate receives
no traffic until health and write-block checks pass. The public cloud revision
disables live trading, paper writes, and unauthenticated analysis POSTs; MT5
continues to run only on the persistent Windows host.

See [Google Cloud deployment](docs/GOOGLE_CLOUD_DEPLOY.md).

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
## ATLAS Trading AI Demo

ATLAS is a deterministic multi-asset trading-analysis demo cockpit.

It shows live market-data analysis, ATLAS scoring, risk-gated decisions, and paper-trading candidate status.

> Safety boundary: this repository does **not** place live trades from the dashboard demo. The demo is for analysis, testing, and paper-trading validation only.

## Current demo features

- Live market-data dashboard
- ATLAS decision matrix
- Long/short scoring
- Risk vetoes
- Trade-gate candidate status
- Paper/demo mode
- Multi-asset watchlist:
  - XAUUSD
  - SILVER
  - GAS
  - EURUSD
  - SOLUSDT
  - XRPUSDT

## Quick start on Windows PowerShell

From the project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:ATLAS_LIVE_TRADING="false"
$env:ATLAS_DASHBOARD_ONLY="true"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload
```

Open:

```text
http://127.0.0.1:8010/dashboard
```

## Run tests

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest tests/test_atlas_scoring_engine.py tests/test_atlas_pipeline_integration.py tests/test_atlas_trade_gate.py tests/test_atlas_dashboard_demo.py -v
```

Expected result:

```text
22 passed
```

## Let friends try it from your computer on the same Wi-Fi

1. Start the server on all local interfaces:

```powershell
.\.venv\Scripts\Activate.ps1
$env:ATLAS_LIVE_TRADING="false"
$env:ATLAS_DASHBOARD_ONLY="true"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8010
```

2. Find your local IP:

```powershell
ipconfig
```

Look for your Wi-Fi IPv4 address, for example:

```text
192.168.1.45
```

3. Friends on the same Wi-Fi open:

```text
http://192.168.1.45:8010/dashboard
```

Replace `192.168.1.45` with your real IPv4 address.

## Windows firewall note

If friends cannot open the page, Windows Firewall may be blocking Python/Uvicorn. Allow Python on Private networks only.

Do not expose this demo publicly with real credentials or trading permissions.

## Recommended sharing options

### Option A — GitHub sharing

Send friends the repository link and this command path:

```powershell
git clone https://github.com/imsamtaha/Trading-ai.git
cd Trading-ai
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:ATLAS_LIVE_TRADING="false"
$env:ATLAS_DASHBOARD_ONLY="true"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

### Option B — Same Wi-Fi live demo

Run the server with:

```powershell
$env:ATLAS_LIVE_TRADING="false"
$env:ATLAS_DASHBOARD_ONLY="true"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8010
```

Then share your local network URL:

```text
http://YOUR_IPV4_ADDRESS:8010/dashboard
```

### Option C — Screen-share demo

Use Zoom, Google Meet, Discord, or WhatsApp screen share and keep the app running locally.

This is the safest method while the system is still in validation mode.

## Production warning

Before any real-money use, ATLAS still requires:

- Historical backtesting
- Out-of-sample validation
- Persistent demo journaling
- Broker/MT5 read-only verification
- Explicit execution authorization layer
- Hard kill-switch and account-risk controls

The current version is a strong demo, not a licensed financial advisory or autonomous live-trading product.
