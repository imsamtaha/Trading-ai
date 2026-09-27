# ATLAS frontend deployment and rollback

## Current state

The production Cloudflare Tunnel sends `justai-atlas.online` to `http://127.0.0.1:8011` in `C:\Users\KHAT W TELEPHONE\.cloudflared\config.yml`. That is the existing FastAPI process. The old site remains live until an explicit routing change is approved.

## Proposed topology

Run Next.js on `127.0.0.1:3000` and FastAPI on `127.0.0.1:8011` on the same trusted machine. Next serves `/`, `/dashboard`, and `/login`. Its server-side rewrite forwards only five allowlisted `/backend/...` read/chat paths to FastAPI. The browser never receives the backend origin or any private key. Trading/risk execution routes are not called by this frontend. The preexisting Google auth bundle is served by Next at `/legacy-auth.js` from `web/assets/google-auth.js` and binds the same controls on the redesigned `/login`. The existing `/?auth=callback` OAuth return redirects to `/login` while preserving its query. Test the callback with a non-trading account before routing cutover.

## Current blocker

As verified locally on 2026-09-27 after the reported fix, the running server at port 8011 returns 200 for `/health`, but 403 for `/dashboard/atlas`, `/dashboard/chart-data`, `/dashboard/market-briefing`, and `/assets/google-auth.js`. Next shows a degraded account state until this access boundary is understood and the intended account data policy is configured. The dashboard response also lacks daily P/L and risk utilization fields, so those tiles remain explicit placeholders; do not infer risk from account balance or floating profit. Do not weaken FastAPI risk or execution access to clear the gate. Recheck these endpoints and a real Google callback before cutover.

## Gate before routing

From the worktree root, run `python -m pytest -q`. From `web/`, run `npm ci`, `npm test -- --run`, `npm run build`, and `npm run lint`. Inspect `.next/static` for private secret values. Start `npm run start -- --hostname 127.0.0.1 --port 3000` with `ATLAS_BACKEND_ORIGIN=http://127.0.0.1:8011` set in the server process. Check `http://127.0.0.1:3000/login`, `/dashboard`, `/backend/health`, and offline/error states with FastAPI unavailable in a separate staging environment. Confirm callback and session after Google sign-in. Verify phone width and chart symbol/timeframe changes.

## Proposed cutover (approval required)

Back up `config.yml` to a dated file. In the existing `justai-atlas.online` ingress entry, replace only `service: http://127.0.0.1:8011` with `service: http://127.0.0.1:3000`. Validate the tunnel config and restart only the tunnel service. Keep FastAPI on port 8011; no DNS, risk, broker, or execution changes are required. Smoke test HTTPS login, callback, dashboard, chart and API connectivity. Preserve the existing ingress fallback and other hostnames.

## Rollback

Restore the backed-up `config.yml` (or revert that single service value to `http://127.0.0.1:8011`), validate config, restart only the tunnel service, and confirm `https://justai-atlas.online/health` and legacy root. Keep Next stopped or isolated after rollback. Account, MT5 and risk state remain in FastAPI. Do not alter the broker connection during cutover or rollback.
