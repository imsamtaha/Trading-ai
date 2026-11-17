# ATLAS Owner Control Center (/sam)

## Scope

The owner route lives in the **private ATLAS FastAPI application**; the
independent ChatGPT Sites publication has **not** been changed by this
repository work. Do not claim a Sites URL or custom domain is live until its
own deployment source and owner authentication are verified.

The page is Arabic-default, mobile RTL, bilingual, and read-only. It provides
Overview, Council Agents, MT5 DEMO status, Signals, Risk Controls, Training
Progress, Decision Evidence, PAPER Trade History, Windows Runtime, and Shadow
Learning, with Refresh, History, search, sorting and before/after comparison
slots. Nothing writes to MT5, runs the worker, or touches broker credentials.

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
