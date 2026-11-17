# ATLAS deployment and execution status

Date: 2026-09-12 · Branch: `arena/01a0948f-trading-ai` · Base: `main` @ `7b23c58`

## What is running

| Surface | Process | Bind | Notes |
| --- | --- | --- | --- |
| Private ATLAS app (FastAPI, cockpit + API) | `ATLAS app (FastAPI)` | `0.0.0.0:8000` | `ATLAS_LIVE_TRADING=false`, `ATLAS_DASHBOARD_ONLY=true` |
| Public ATLAS Market website (static) | `ATLAS Market website (static)` | `0.0.0.0:4173` | serves the validated `out/` package |

Both are exposed as live previews. Restart either with:

```sh
cd /home/user/Trading-ai
ATLAS_LIVE_TRADING=false ATLAS_DASHBOARD_ONLY=true /home/user/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

/home/user/.venv/bin/python scripts/build_website.py
cd out && python3 -m http.server 4173 --bind 0.0.0.0
```

## Endpoint verification (live)

Healthy (200): `/health`, `/api`, `/docs`, `/openapi.json`, `/dashboard/demo-status`,
`/dashboard/market-briefing`, `/dashboard/markets`, `/agent/capabilities`,
`/agent/right-hand/capabilities`, `/assets/{site.css,site.js,demo-model.js,favicon.svg,google-auth.js}`,
`/ui/{preferences,agent-panel,demo-panel}.js`.

Blocked by the dashboard-only guard (403, as designed): `/mt5/status`,
`/mt5/positions`, `POST /mt5/test-order`, `/subscription/plans`.

Degraded because this sandbox has no broker terminal and no outbound market
data: `/dashboard/atlas` returns 503 `MetaTrader5 package is unavailable`,
and `/dashboard/market-briefing` returns `DEGRADED` with provider TLS errors.
Requests carrying a preview-style `Host` header return 200.

## Pipeline execution (synthetic, paper-only)

`scripts/atlas_offline_cycle.py` drives the production analysis code paths with
locally generated candles (no MT5, no provider):

```sh
ATLAS_LIVE_TRADING=false ATLAS_DASHBOARD_ONLY=true \
python scripts/atlas_offline_cycle.py --reset-ledger
```

Result of the recorded run (seed 7, 5m, 6 watchlist symbols):

- Gates: 3 `PAPER_TRADE_OPENED`, 1 `NO_TRADE`, 2 `SKIPPED` (ledger cap of 3
  concurrent simulated positions).
- Opened: XAUUSD SHORT (confidence 95), XAGUSD SHORT (95), EURUSD SHORT (100).
- Settled against follow-up quotes: EURUSD `TAKE_PROFIT` +2.07R, XAUUSD
  `STOP_LOSS` −1.08R, XAGUSD `STOP_LOSS` −1.32R.
- Readiness gate: `CONTINUE_FORWARD_DEMO`, 3 of 25 required closed trades,
  `automatic_live_activation: false`.

Every field is labelled `SYNTHETIC_LOCAL`, `live_orders_sent: false`. This is a
pipeline check, **not** market data and **not** a performance claim. The ledger
it writes (`data/atlas_offline_ledger.json`) is separate from the MT5 demo
ledger, so a sandbox run can never be mistaken for broker activity.

## Validation

| Check | Result |
| --- | --- |
| `python -m pytest -q` | 193 passed, 0 failed |
| `node --test tests/test_demo_model.cjs` | 3 passed |
| `node --test tests/test_google_auth.mjs` | 7 passed |
| `node --check web/assets/{site.js,google-auth.js}` | clean |
| `python scripts/build_website.py` | 7 public files validated into `out/` |

The suite is green against current `main`, which also carries the fixes for the
three mismatches visible on the older base commit (`/` serving the cockpit and
Stripe still reported by `/billing/methods`); those tests were updated upstream
in `7b23c58` and now pass unmodified.

## Open items

1. **Market data is unreachable from this sandbox** (Yahoo/Binance TLS blocked),
   so live boards and MT5 telemetry stay empty here; they need the Windows MT5
   host and normal egress.
2. **No external host deployment yet**: `vercel`/`netlify` CLIs and tokens are
   not present. `vercel.json`, `netlify.toml`, and `out/` are ready for a
   Git-connected or static upload, and the app runs locally on port 8000.
