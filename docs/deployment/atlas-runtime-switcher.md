# ATLAS runtime switcher
Owner panel: https://justai-atlas.online/admin/runtime
Dashboard: https://justai-atlas.online/dashboard
Sign in as the configured ATLAS_OWNER_EMAIL.

## Windows start button
Desktop shortcut: ATLAS START.lnk.
```powershell
powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File "C:\Users\KHAT W TELEPHONE\Trading-ai\.worktrees\atlas-clean-followup\scripts\ATLAS-Switcher.ps1"
```
START ATLAS starts the existing backend and frontend scheduled tasks only when health checks fail, verifies backend identity on port 8012, then the owner frontend on 8011.
Healthy services are not started twice. An occupied port with an unhealthy/older service is reported rather than replaced.
Use -Action Status for JSON status or -Action Start for command-line startup.
The existing Cloudflare Tunnel must run for the public URL.

## Owner controls
GET /api/runtime/status, POST /api/runtime/demo-execution, and POST /api/runtime/restart remain protected by the backend owner check.
The browser uses /backend rewrites and the existing HttpOnly session cookie. Credentials stay server-side.
The demo switch enables/disables existing demo order permission; it does not connect MT5, start an autonomous council loop, or close positions.
Restart compares the process instance_id with the pre-restart value. The old ONLINE process cannot confirm success or restore controls.
The companion backend fix is PR #67. Legacy backends without instance_id disable the restart button.
Network failures clear availability; mutations are never retried automatically. Live execution remains LOCKED.

## Verified deployment, 2026-10-01
78 frontend tests, 178 backend tests, ESLint and the production build passed. Read-only code review accepted the restart race correction.
Build directory: .next-runtime-instance-20261001.
Frontend task: ATLAS Web Frontend, launcher web/run-runtime-production.ps1, port 8011.
Backend task: ATLAS Private Backend, atlas-private-multiuser worktree, port 8012.
Staging: login, dashboard, runtime page and proxied health returned 200. Anonymous runtime APIs returned 401.
The backend restarted into a new process and the public proxied health returned 200.
The public owner panel served the matching BUILD_ID. Windows -Action Start returned Backend=true and Frontend=true without duplicating healthy services.
No authenticated broker order or real-money execution was submitted.

## Rollback
Previous frontend task XML: C:\Users\KHAT W TELEPHONE\ATLAS_Backup\ATLAS-Web-Frontend-pre-runtime-20261001.xml.
Original launcher: C:\Users\KHAT W TELEPHONE\Trading-ai\.worktrees\atlas-webapp-option-a\web\run-production.ps1.
Restore that launcher as the ATLAS Web Frontend task action, stop that task, then start it. The original .next-release4 build remains available.
The intermediate .next-runtime-final-20261001 build also remains available. Its restart UI does not compare instance IDs.
Cloudflare routing and all live execution flags were unchanged.
