# ATLAS web deployment and rollback

## Live topology (2026-09-28)

The Cloudflare Tunnel still forwards `justai-atlas.online` to `http://127.0.0.1:8011`. Its active connectors run with token files and are managed remotely. The local `C:\Users\KHAT W TELEPHONE\.cloudflared\config.yml` was not changed and is not the active ingress control.

Next.js serves `127.0.0.1:8011` from `.worktrees/atlas-webapp-option-a/web`. Exact `/backend/*` rewrites in the production build forward health, private dashboard/chart/briefing/assistant, and auth routes to FastAPI on `127.0.0.1:8012`. FastAPI runs from `.worktrees/atlas-private-multiuser` with `ATLAS_LIVE_TRADING=false`, `ATLAS_DASHBOARD_ONLY=true`, and `MT5_REQUIRE_DEMO=true`. The existing Cloudflare tunnel and trading execution code are unchanged.

## Start and verify

Backend runner: `C:\Users\KHAT W TELEPHONE\ATLAS_Backup\run-atlas-private-api.ps1` (port 8012). Frontend runner: `web/run-production.ps1` (port 8011). These currently run as user processes; after a Windows restart, start the backend first, then the frontend, and check both health endpoints. Do not start the old port 8011 FastAPI runner while Next occupies that port.

Build Next with `ATLAS_BACKEND_ORIGIN=http://127.0.0.1:8012` set in the build process. The build manifest must route `/backend/api/user/assistant` and `/backend/auth/session` to port 8012. Run `npm test -- --run`, `npm run lint`, `npm run build`, and backend `python -m pytest -q` before rebuilding or restarting.
Public smoke checks: `/login`, `/dashboard`, `/health`, and `/backend/health` return 200; `/backend/api/user/dashboard`, `/backend/api/user/chart-data`, `/backend/api/user/market-briefing`, and a valid anonymous POST to `/backend/api/user/assistant` return 401. Direct `/api/user/dashboard` and `/dashboard/atlas` return 404 from Next. The `/?auth=callback&code=...` redirect preserves the code at `/login`.

The Google provider is enabled in Supabase and the live login renders its Google button. A complete Google sign-in, secure `atlas_session` cookie, and signed-in dashboard still require a real account test. Do not claim that final step is verified until it is observed.

## Rollback

1. Stop the Node/Next process listening on `127.0.0.1:8011` (identify it by port and command line); leave FastAPI on 8012 running.
2. Run the original `C:\Users\KHAT W TELEPHONE\ATLAS_Backup\run-atlas-private.ps1` to restore FastAPI on port 8011.
3. Check `https://justai-atlas.online/health` and the legacy `/login`. The Cloudflare tunnel needs no change.
4. Stop the spare FastAPI process on port 8012 after the restored service is healthy.

The private backend worktree contains pre-existing uncommitted changes to its demo dashboard and repository. Preserve those files during rollback; no destructive checkout or broker state change is needed.
