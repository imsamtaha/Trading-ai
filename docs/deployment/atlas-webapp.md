# ATLAS web app deployment contract

## Current state

The Next.js app is a separate static export under `web/out`. The legacy public root and FastAPI dashboard remain the current production surfaces. No DNS, hosting route, reverse proxy, or execution configuration was changed as part of this implementation.

## Route map

| Browser request | FastAPI route | Purpose |
| --- | --- | --- |
| `/health` | `/health` | Service liveness |
| `/dashboard/mt5-state` | `/dashboard/mt5-state` | Account, mode, positions, read-only signals |
| `/dashboard/market-briefing` | `/dashboard/market-briefing` | Market board and headlines |
| `/market/{symbol}/candles` | `/market/{symbol}/candles` | OHLCV history |
| `/mt5/positions` | `/mt5/positions` | Open positions |
| `/agent/right-hand/chat` | `/agent/right-hand/chat` | Analysis assistant |

Prefer serving the frontend and proxying these API paths through the same origin. If the API is on another origin, set `NEXT_PUBLIC_ATLAS_API_BASE_URL` at build time and configure FastAPI's ingress CORS allowlist for the exact frontend origin. Never expose MT5/OpenAI keys, owner authorization, or execution tokens to the browser.

## Build and health checks

From `web/`, run `npm ci`, `npm test -- --run`, `npm run lint`, and `npm run build`. Serve the generated `out/` directory as static files, including directory-style routes such as `/markets/` and `/dashboard/`. The status chip reports **online** only when both `/health` and account state work, **degraded** when health works but account state fails, and **offline** when health fails.

## Staged cutover

1. Deploy `web/out` to an internal/staging host with the production-like API route map.
2. Verify online, degraded, and offline states; live account values against the existing dashboard; market candles after symbol and interval switches; assistant success/failure; phone-width layout; and browser assets for private values.
3. Confirm the exact production route/proxy target and rollback owner before routing a public path to the new app.
4. Keep the current root/dashboard available through the rollout.

## Rollback

Restore the previous ingress/static root mapping to the existing server-rendered dashboard/public website. The frontend is read-only for account/market/risk state and uses the existing analysis-only chat endpoint. It does not migrate or write trading, risk, or account data, so rollback requires no state restoration.
