# ATLAS Whish and MT5 deployment, 2026-09-28

Cloudflare Tunnel remains `justai-atlas.online -> http://127.0.0.1:8011`.
Next.js is the frontend on 8011; FastAPI remains loopback-only on 8012.
`run-production.ps1` selects `.next-release2` and sets `ATLAS_BACKEND_ORIGIN=http://127.0.0.1:8012`.
No Cloudflare config edit or trading execution flag change is part of this release.

Verification before cutover: 57 Vitest tests, 141 pytest tests, Next production build and ESLint passed. The final staged Next build served on 3002; FastAPI on 8012 returned health and public preview 200, unauthenticated private and owner routes 401. Public smoke returned 200 for login, dashboard, subscription, health and preview; owner queue returned 401 without a session. Static JavaScript had no service key, SMTP password, MT5 password or real-money acknowledgement.

Rollback:
1. Copy `C:\Users\KHAT W TELEPHONE\ATLAS_Backup\run-production-pre-whish-20260928.ps1` over `web\run-production.ps1`.
2. Restart only the `ATLAS Web Frontend` scheduled task. The previous `web\.next` build remains available; a second backup is at `C:\Users\KHAT W TELEPHONE\ATLAS_Backup\next-pre-whish-20260928-1805`.
3. Verify `/login`, `/dashboard` and `/backend/health` through HTTPS. Supabase migration is intentionally kept: customer subscription writes stay revoked, and the owner approval RPC is unused by the previous frontend.

Customers can open a prefilled email to imsamtaha.ai@gmail.com from the Whish request page and attach the receipt. Sending depends on their email app; the request remains pending until owner approval. Automatic Whish review notifications need `ATLAS_SMTP_HOST`, `ATLAS_SMTP_PORT`, `ATLAS_SMTP_FROM`, `ATLAS_SMTP_USER`, and `ATLAS_SMTP_PASSWORD` in the backend process environment. Until configured, pending requests remain in the owner queue at `/admin/whish` without an email notification. Verify Whish payment independently before approval.

## Manual MT5 trading candidate, 2026-09-28

The manual order UI and private API are deployed in `.next-release4` and the backend branch. Orders remain disabled in the production backend launcher: `ATLAS_USER_DEMO_ORDERS=false`, `ATLAS_USER_REAL_ORDERS=false`, and legacy execution flags remain false. The UI accurately reports the disabled state. Broker passwords remain process-memory only, so account connection requires re-entry after restart.

Gates: backend 154/154 pytest, web 60/60 Vitest, lint and Next build passed. Secret scan of `.next-release4/static` returned no service-role key, SMTP password, MT5 password or real-money acknowledgement. Staging on 3003 returned dashboard/login/health 200 and unauthorized trading state 401; public routes returned 200 after cutover. Persistent, credential-free audit path is `C:\Users\KHAT W TELEPHONE\ATLAS_Backup\manual_mt5_orders.sqlite3`.

Activation requires a dedicated or serialized FxPro terminal that cannot be switched by the other Python servers on this host, then an authenticated Demo and Real account acceptance test with the owner present. Do not enable either order flag on the shared terminal. Real also needs the explicit acknowledgement and per-account activation. No real broker order has been submitted or verified.

Rollback only the frontend: copy `C:\Users\KHAT W TELEPHONE\ATLAS_Backup\run-production-pre-manual-20260928.ps1` to `web\run-production.ps1` and restart `ATLAS Web Frontend`. Backend rollback: copy `C:\Users\KHAT W TELEPHONE\ATLAS_Backup\run-atlas-private-api-pre-manual-20260928.ps1` to `run-atlas-private-api.ps1` and restart `ATLAS Private Backend`; leave order flags false. Cloudflare stays on port 8011.
