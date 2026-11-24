# ATLAS Owner Control Center (/sam)

## Scope

The owner route lives in the **private ATLAS FastAPI application**; the
independent ChatGPT Sites publication has **not** been changed by this
repository work. Do not claim a Sites URL or custom domain is live until its
own deployment source and owner authentication are verified.

The page is Arabic-default, mobile RTL, bilingual, and read-only. It provides
Overview, Council Agents, Accounts, Signals, Risk Controls, Training
Progress, Decision Evidence, PAPER Trade History, Windows Runtime, and Shadow
Learning, with Refresh, History, search, sorting and before/after comparison
slots. The Accounts view reads demo account information using private,
view-only cTrader authorization.

This change **does not delete** older public dashboards, billing code,
compatibility routes, worker scripts, data, or existing Sites publications.

## Activation (private authenticated host only)

Use an HTTPS reverse proxy or private tunnel terminating TLS before exposing
HTTP Basic authentication beyond loopback. **Never publish the /sam folder as a
static public website**, which would bypass server authentication.

The private server requires:

- `ATLAS_OWNER_DASHBOARD_USER`: owner-only login name.
- `ATLAS_OWNER_DASHBOARD_PASSWORD`: unique strong secret.
- `ATLAS_OWNER_SNAPSHOT_HMAC_KEY`: shared secret, at least 32 characters.
- `ATLAS_OWNER_SNAPSHOT_PATH`: absolute path to the signed snapshot JSON.
- `ATLAS_LIVE_TRADING=false`, `ATLAS_DASHBOARD_ONLY=true`.

Store all secrets outside Git and never expose them through public APIs, logs
or Sites. No authentication values ship with the code; the route returns 503
until owner credentials are configured. The snapshot endpoint returns
`UNAVAILABLE` if no signed export exists.

On the verified Windows PAPER host, after checking the MT5 terminal is DEMO
and the worker/ledger is readable, run from the project's existing venv:

```powershell
python scripts/export_owner_paper_snapshot.py --root . --output data/atlas_owner_snapshot.json
```

The export consumes existing `data/atlas_demo_status.json`,
`data/atlas_demo_ledger.json` and, when present, the Council profile,
training JSONL, and signal JSONL. It **does not** change the ledger, train an
agent or send a trade. Worker status and PAPER ledger are required; a missing
or corrupted source stops the export. An old heartbeat makes the displayed
snapshot STALE (after six hours), even if exported recently.

The exported JSON is signed with HMAC-SHA256 using the shared environment key.
The backend validates signature, source environment, broker-execution flag,
timestamp and payload shape before displaying anything. The HMAC confirms the
snapshot's origin/integrity, **not** that returns or model quality are independently
audited. Signed rows are reduced to an allowlist of fields and capped at 500
per table. The login is never returned in full by this integration.

No unsupported performance comparison is invented: before/after training
metrics remain empty unless separately evidenced and signed. Council
confidence comes from actual training opinions; weights come from the PAPER
profile. Profit/loss fields are risk-multiple PAPER estimates only, never
broker profit. An empty section means *unavailable*, not zero performance.

## cTrader demo workspace

### Separate business, support, and Whish identities

- ATLAS private cTrader owner: `business.samirtaha@gmail.com`.
- The primary public/support mailbox **remains** `info@justai-atlas.online`.
- Whish payment approval, manual review, and admin notification email **remain** `ImSamtaha.ai@gmail.com`; do not change the existing `ADMIN_EMAIL`, older Supabase Whish approval migration, or receipt destination.
- Whish payment funds are received according to the configured Whish recipient, not an email address. No payout, banking, or payment credentials are changed here.
- Intended FxPro **cTrader DEMO** account login: configure the owner-supplied login in the private environment variable `ATLAS_CTRADER_DEMO_LOGIN` (never in public source files). Grant only `SCOPE_VIEW` account authorization. Email ownership alone does not authenticate a cTrader account.

The old MT5/FxPro integration stays paused on the ATLAS application. A separate historical Windows worker must be stopped independently if running; changing a Git branch does not stop an external process. cTrader Demo account balances are broker metadata only. Existing MT5/PAPER ledger records cannot be presented as FxPro cTrader trade history.

Deployment/identity cutover requires login confirmation for the business email, OAuth consent for the specified demo account, validated read-only telemetry and owner authorization. Neither browser sign-in nor cTrader consent is completed by this code change.


Choose `ATLAS_BROKER_PROVIDER=ctrader` on the private ATLAS application to
select cTrader and pause MT5 connections. An independent Windows worker needs
the same setting or a controlled stop on its own host. In an MT5 deployment,
`ATLAS_MT5_CONNECTIONS_PAUSED=true` also blocks MT5.

Set `ATLAS_OWNER_DASHBOARD_USER` to the intended primary workspace login and
`ATLAS_MT5_WORKSPACE_EMAIL` to the optional MT5 identity. The optional identity
is a private display label. The existing owner password remains the
authentication mechanism.

Configure the cTrader login shown in the app in `ATLAS_CTRADER_DEMO_LOGIN`.
Store the approved application credentials `ATLAS_CTRADER_CLIENT_ID` and
`ATLAS_CTRADER_CLIENT_SECRET`, and a fresh `ATLAS_CTRADER_ACCESS_TOKEN` from
the cTrader Open API `accounts` authorization, in the private runtime secret
store. Select the intended demo account on the consent screen. Rotate
credentials through the Open API portal and update the runtime when required.

The owner page’s Accounts tab queries the demo endpoint on request. It shows
the masked cTrader login and account information with the existing signed
PAPER history and training results alongside it. Broker demo activity is never
imported as PAPER results. The existing signed Windows PAPER export remains
the source of the history and training figures.

[cTrader Open API authentication](https://help.ctrader.com/open-api/account-authentication/)

## Validation and acceptance

```
python -m pytest -q tests/test_owner_dashboard.py
python -m pytest -q
```

Perform manual browser checks at `/sam` on mobile RTL and desktop EN,
including table sort/filter, Refresh, History, and empty-data state. Confirm
the unauthenticated page/API return 401, the unconfigured host returns 503,
and broker order POSTs are blocked by dashboard-only mode. Confirm a real
Windows heartbeat, source fingerprint, paper-ledger read and file permissions
before reporting production data verified.

## Deployment boundaries

The existing website `justai-atlas.online/sam` is **not** proven to be served
by this FastAPI router. Deploy or route **only after verifying** the
original host, HTTPS, owner auth, signed evidence flow, and Windows runtime.
Do not publish these authenticated records through public Sites or expose
the HMAC secret in frontend JavaScript. Keep all trading execution disabled.
