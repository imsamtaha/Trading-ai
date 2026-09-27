# ATLAS frontend deployment and rollback

## Current state

The production Cloudflare Tunnel sends `justai-atlas.online` to `http://127.0.0.1:8011` in `C:\Users\KHAT W TELEPHONE\.cloudflared\config.yml`. That process is launched by `ATLAS_Backup/run-atlas-private.ps1` from `.worktrees/atlas-private-multiuser` (branch `feat/atlas-private-multiuser`). After the device interruption, the same private service script was restarted on port 8011. On 2026-09-28, local and public `/health` and `/login` returned 200. No tunnel change has been made.

## Proposed topology

Run Next.js on `127.0.0.1:3000` and FastAPI on `127.0.0.1:8011` on the same trusted machine. Next serves `/`, `/dashboard`, and `/login`. Its server-side rewrite forwards exact health, private user dashboard/chart/briefing, and auth paths to FastAPI. The browser never receives the backend origin or any private key. Trading/risk execution routes are not called by this frontend. The redesigned `/login` uses the private backend's Supabase public config. With `GOOGLE_CLIENT_ID` it uses Google ID tokens; without it, Supabase Google OAuth returns through the existing `/?auth=callback` redirect. Email OTP uses the same callback. The browser exchanges the resulting access token for an HttpOnly `atlas_session` cookie. Test both Google and email callback with a non-trading account before routing cutover.

## Current blocker

The running private FastAPI process intentionally returns 403 for shared `/dashboard/atlas`. This must remain blocked. Its authenticated `/api/user/dashboard` returns 401 without a session and isolates user MT5 demo data. Authenticated `/api/user/chart-data` and `/api/user/market-briefing` are running after the same private service restart; anonymous requests returned 401 locally and publicly. The private backend currently has no right-hand AI chat route, so the assistant remains unavailable. Daily P/L and risk utilization remain explicit placeholders where the private API has no verified values. A real Google callback and the production session cookie have not been exercised end to end.

## Gate before routing

From the worktree root, run `python -m pytest -q`. From `web/`, run `npm ci`, `npm test -- --run`, `npm run build`, and `npm run lint`. Inspect `.next/static` for private secret values. Start `npm run start -- --hostname 127.0.0.1 --port 3000` with `ATLAS_BACKEND_ORIGIN=http://127.0.0.1:8011` set in the server process. Check `http://127.0.0.1:3000/login`, `/dashboard`, `/backend/health`, and that `/backend/api/user/dashboard` returns 401 anonymously. Verify user A cannot see user B's dashboard, then confirm the secure callback/session after real Google and email sign-in on HTTPS. Verify chart/briefing and phone width. Keep the shared MT5 telemetry route at 403.

## Proposed cutover (approval required)

Back up `config.yml` to a dated file. In the existing `justai-atlas.online` ingress entry, replace only `service: http://127.0.0.1:8011` with `service: http://127.0.0.1:3000`. Validate the tunnel config and restart only the tunnel service. Keep FastAPI on port 8011; no DNS, risk, broker, or execution changes are required. Smoke test HTTPS login, callback, dashboard, chart and API connectivity. Preserve the existing ingress fallback and other hostnames.

## Rollback

Restore the backed-up `config.yml` (or revert that single service value to `http://127.0.0.1:8011`), validate config, restart only the tunnel service, and confirm `https://justai-atlas.online/health` and legacy root. Keep Next stopped or isolated after rollback. Account, MT5 and risk state remain in FastAPI. Do not alter the broker connection during cutover or rollback.
