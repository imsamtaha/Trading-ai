# ATLAS MT5 Forward-Demo Worker

## Architecture

ATLAS runs its decision logic in Python. A persistent Windows worker owns the
MetaTrader 5 terminal connection. During forward-demo validation, it never
sends an MT5 order. Instead, it opens qualified candidates in a local paper
ledger, evaluates them using subsequent MT5 quotes, and stores every material
open/close/error event in Supabase when credentials are available.

`ATLAS -> Scoring/Risk Gate -> Paper Ledger -> MT5 Quotes`

`MT5 Worker -> local JSONL + Supabase audit events`

## Windows setup

For the reconnecting background worker and dashboard, see
[Demo operations and live-review handoff](docs/DEMO_OPERATIONS.md) and run
`scripts/start_demo_session.ps1` after setup. This session publishes worker
freshness and paper-ledger progress to `/dashboard/demo-status`.

1. Install MetaTrader 5 and log into a **demo** account.
2. Clone this repository on the same Windows machine where MT5 is installed.
3. Create `.env` from `.env.mt5.example`.
4. Set `MT5_TERMINAL_PATH`, `MT5_LOGIN`, `MT5_PASSWORD`, and `MT5_SERVER`.
5. Set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` to the project values. Never commit `.env` or that key.
6. Install dependencies: `python -m pip install -r requirements.txt`.
7. Verify the terminal connection: `python scripts/verify_mt5.py`.
8. Run one safe connected cycle: `python run_atlas_mt5.py --once`.
9. Start continuous forward-demo registration: `python run_atlas_mt5.py`.
10. Inspect progress at any time: `python scripts/atlas_demo_status.py`.

The PowerShell shortcut is:

```powershell
.\scripts\start_atlas_demo.ps1
```

## Recorded trade lifecycle

- `PAPER_TRADE_OPENED`: strategy, unified decision, and risk gates all approved an entry.
- `PAPER_TRADE_CLOSED`: an MT5 quote touched the paper position's stop loss or take profit.
- `NO_TRADE` and `SKIPPED`: kept in the local signal journal; optional Supabase persistence is enabled with `ATLAS_PERSIST_ALL_SIGNALS=true`.
- `MT5_ERROR` / `ERROR`: persisted for diagnosis.

The durable local records are `data/atlas_demo_ledger.json` and
`data/atlas_signals.jsonl`. Supabase material events are written to
`public.atlas_execution_events`.

## Safety

`ATLAS_LIVE_TRADING=false` is mandatory for this runner. If it is changed to
`true`, the runner exits before connecting. The worker uses MT5 only for
account metadata, symbols, and quotes; it does not invoke the MT5 order API.

A paper ledger is not a broker fill record and its P&L is explicitly
risk-normalized. It is appropriate for validating signal quality and process,
not for claiming live trading performance.

## Live-review gate

The status report requires at least 25 **closed** paper trades, positive
expectancy, profit factor of at least 1.10, and drawdown within the configured
limit. Passing these checks produces `REVIEW_REQUIRED`; it never enables live
trading automatically. Live execution also requires out-of-sample validation,
MT5 lot-size conversion tests, order reconciliation, daily-loss limits, and a
manual owner approval.

## Tiger Shield read-only provider status

The Tiger Shield Connection Center uses authenticated GET requests to the
provider status endpoints. Serve them from a private listener exposed over
authenticated HTTPS to the Site. Set `ATLAS_PROVIDER_STATUS_TOKEN` on the
service and the corresponding `ATLAS_MT5_DEMO_STATUS_TOKEN`,
`ATLAS_MT5_REAL_STATUS_TOKEN` or `ATLAS_CTRADER_STATUS_TOKEN` in Sites.

- Run the separate read-only Windows status service with
  `python -m uvicorn scripts.atlas_provider_status:app --host 127.0.0.1 --port 8766`. Point
  `ATLAS_MT5_DEMO_STATUS_URL` and `ATLAS_MT5_REAL_STATUS_URL` at the respective
  `/status/mt5` URLs. Use separate bridge processes and terminal installations
  for DEMO and REAL. Set `ATLAS_MT5_STATUS_ACCOUNT_TYPE` to `DEMO` or `REAL`,
  and set that instance's `MT5_TERMINAL_PATH`, `MT5_LOGIN` and `MT5_SERVER`.
  Sign in to the terminal with investor/read-only credentials. The status
  route verifies the active account and environment. The existing
  `/telemetry` route is DEMO-only and should not be routed to the real instance.
- Point `ATLAS_CTRADER_STATUS_URL` at `/status/ctrader` on a service instance
  with `ATLAS_CTRADER_DEMO_LOGIN`, `ATLAS_CTRADER_CLIENT_ID`,
  `ATLAS_CTRADER_CLIENT_SECRET` and an `ATLAS_CTRADER_ACCESS_TOKEN` with
  account-view permission. This route reads the matching FxPro demo account
  without changing the active provider.
- Set `ATLAS_PROVIDER_OWNER_EMAIL` and the optional
  `ATLAS_CTRADER_ACCOUNT_EMAIL` privately in Sites. These email settings
  identify the dashboard owner and the optional provider account. Provider
  authorization comes from the terminal session or cTrader credentials.

On the PAPER worker, `scripts/start_atlas_demo.ps1 -ShadowTraining` enables
shadow evaluation alongside the default Council calibration. The shadow
selection is observational and leaves the PAPER decision authority unchanged.

## FxPro cTrader DEMO and LIVE account status on Linux (no MT5 terminal)

ATLAS also supports two **strictly read-only** FxPro cTrader account connections
from AWS/Linux. These are status readers, **not** broker execution engines.
They do not place DEMO orders or LIVE orders, and they do not feed broker
balances into the PAPER trading ledger.

Official cTrader docs:
- [Separate endpoints](https://help.ctrader.com/open-api/proxies-endpoints/):
  `demo.ctraderapi.com:5036` and `live.ctraderapi.com:5036` for JSON/WebSocket.
- [Account authentication](https://help.ctrader.com/open-api/account-authentication/):
  request OAuth `scope=accounts` (view-only), **never** `scope=trading`.

### Credentials (private runtime only)

Each environment requires its own authorized FxPro cTrader account login and
**view-only** access token, plus the associated Open API application's client
ID and secret. Never put tokens, passwords or private IDs into GitHub,
ChatGPT messages, browser JavaScript, or public Site settings.

| Connection | Runtime settings | Read-only endpoint |
| --- | --- | --- |
| DEMO | `ATLAS_CTRADER_DEMO_LOGIN`, `ATLAS_CTRADER_CLIENT_ID`, `ATLAS_CTRADER_CLIENT_SECRET`, `ATLAS_CTRADER_ACCESS_TOKEN` | `GET /status/ctrader/demo` (also `/status/ctrader` for legacy clients) |
| LIVE | `ATLAS_CTRADER_LIVE_LOGIN`, `ATLAS_CTRADER_LIVE_CLIENT_ID`, `ATLAS_CTRADER_LIVE_CLIENT_SECRET`, `ATLAS_CTRADER_LIVE_ACCESS_TOKEN` | `GET /status/ctrader/live` |

The private API service requires `ATLAS_PROVIDER_STATUS_TOKEN` for the
DEMO route and an **independent** `ATLAS_PROVIDER_LIVE_STATUS_TOKEN` for the
LIVE route. The LIVE route refuses DEMO status tokens, unauthorized accounts,
DEMO accounts, non-FxPro broker accounts, and OAuth trading scopes.
Neither status route accepts POST or provides order placement.

Keep these PAPER guards in the server environment:

```bash
export ATLAS_LIVE_TRADING=false
export ATLAS_ENVIRONMENT=paper
export ATLAS_DASHBOARD_ONLY=true
export ATLAS_AGENT_PAPER_EXECUTION_ENABLED=false

# Set credentials and distinct status tokens privately before starting.
# Use AWS Secrets Manager or private environment variables; never commit them.
python3 -m uvicorn scripts.atlas_provider_status:app --host 127.0.0.1 --port 8766
```

Verify from the same host after configuring the view-only credentials:

```bash
curl -fsS -H "Authorization: Bearer $ATLAS_PROVIDER_STATUS_TOKEN" \
  http://127.0.0.1:8766/status/ctrader/demo
curl -fsS -H "Authorization: Bearer $ATLAS_PROVIDER_LIVE_STATUS_TOKEN" \
  http://127.0.0.1:8766/status/ctrader/live
```

A successful response is marked `"access": "READ_ONLY"` and
`"brokerOrders": false`. It contains only environment, timestamp, broker,
currency, and balance; it does **not** return account numbers or access tokens.
Before configured authorization, the route returns 401 or 503 instead.

To display both independently inside a separately deployed Tiger Shield Site,
wire its server-side integration to `ATLAS_CTRADER_STATUS_URL` and
`ATLAS_CTRADER_LIVE_STATUS_URL`, with matching server-side bearer tokens.
Protect external access with authenticated HTTPS and never expose this
localhost listener to the public Internet. Site wiring and credential
authorization are **not** performed by this source-code change.

Tests: `python3 -m pytest tests/test_ctrader_demo.py tests/test_ctrader_live_status.py tests/test_provider_status.py -q`.
