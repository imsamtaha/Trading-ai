# ATLAS Web App

This directory contains the new responsive Next.js interface. The existing FastAPI dashboard and static public website remain available while the web app is evaluated.

## Local development

1. Install the repository's Python requirements and start FastAPI from the repository root using the existing project instructions.
2. In this directory, run `npm ci` and `npm run dev`.
3. Leave `NEXT_PUBLIC_ATLAS_API_BASE_URL` blank when the frontend and API share an origin. For a separate API host, set it to the public HTTPS API origin in `.env.local`.
4. Run `npm test -- --run`, `npm run lint`, and `npm run build` before deployment.

The production build is a static export in `out/`. The browser calls the existing read/analysis routes: `/health`, `/dashboard/mt5-state`, `/dashboard/market-briefing`, `/market/{symbol}/candles`, `/mt5/positions`, and `/agent/right-hand/chat`. The frontend contains no broker credentials or execution authorization. Backend risk and execution policy remain authoritative.

## Hosting and cutover

Serve `out/` from the chosen static host. Configure the ingress so the listed API paths reach the existing FastAPI service, or set `NEXT_PUBLIC_ATLAS_API_BASE_URL` to that service's public HTTPS origin and allow the deployed frontend origin through the API's CORS policy. Do not put server secrets in `NEXT_PUBLIC_*` variables.

Use a staging host first. Verify health/account status, offline and degraded states, candles by symbol/timeframe, assistant failure handling, and a narrow mobile viewport. Then route the new app path or root only after the deployment owner confirms the ingress target. Keep the current server-rendered dashboard reachable during cutover. Rollback by pointing the frontend route back to the existing dashboard/static root; no database, account, risk, or execution state migration is involved.

The current repository keeps the public root and deployment configuration unchanged. See `../docs/deployment/atlas-webapp.md` for the route map and readiness checklist.
