# ATLAS production operations

Use `.venv/Scripts/python.exe ops/deploy_atlas_web.py` from the ATLAS root for frontend upgrades. It runs all frontend tests, TypeScript checks and a production build in an isolated directory. It verifies candidate routes and login JavaScript on port 8014 before stopping the production frontend. Failed post-deploy health restores the previous build. One `.next-last-good` build remains available. Builds and credentials belong outside Git.

The Windows supervisor observes backend, frontend, the public route, the paper monitor and MT5. It recovers only the named web and tunnel tasks after three failures, with backoff and bounded restarts. Tunnel recovery requires healthy local services. A deployment maintenance marker prevents recovery from racing the build swap and expires automatically. It starts a stopped Paper Monitor after three observations, with backoff and a five-start budget until a Running task produces a fresh log. Disabled tasks require attention. A running paper task with a stale log is reported and never stopped or restarted. It does not submit broker orders.

Windows rejected changes to the elevated web/backend task settings under the remote session. Run `ops/configure_atlas_host.ps1` in an Administrator PowerShell to remove battery-related stops. The tunnel currently requires a logged-in user. The host must remain powered, connected and awake. The latest outage includes a Windows sleep event with reason Application API; changing idle timeouts cannot guarantee protection against an application or person explicitly putting the host to sleep.

Google OAuth was verified end-to-end on 2026-10-08: the Google button returned to the dashboard and the backend /api/me resolved the authenticated account. The paper monitor was restarted after a stopped task was found; its task is Running and its paper log and ledger updated afterward. The cause of that earlier stop is not yet established. Never commit provider secrets, tunnel tokens, runtime env files or user databases. An enabled login button or HTTP 200 is not evidence of successful OAuth.

Public health probes must identify themselves as `ATLAS-Windows-Monitor/1.0`, as the production supervisor already does. On 2026-10-08 the default Python urllib client received Cloudflare error 1010, while the ATLAS monitor client returned 200 for login, dashboard and backend health. The authenticated browser dashboard also showed backend connected and rendered candles. No Cloudflare security settings were changed.


## 2026-10-10 Windows Paper Ledger incident recovery

The Windows ATLAS Paper Monitor previously failed with WinError 5 during
`Path.replace()` of the canonical ledger. Restart Manager identified a
long-running Node.js Desktop Commander process holding that path. A production
byte-identical test confirmed that `MoveFileEx` failed while `ReplaceFileW`
succeeded with the same target. `MT5PaperLedger._persist()` now tries bounded
replacement retries, then uses Windows `ReplaceFileW` for an existing target;
writes remain atomic, and failed temporary files are cleaned up. Other
platforms remain unchanged. Neither path sends broker orders.

The Windows watchdog now flags `LEDGER_PERSISTENCE_FAILED` when a dated Paper
ledger persistence error is newer than the canonical ledger's successful write.
The failure is sticky across cycles until a newer persisted ledger version
exists, and stopped tasks with an unresolved persistence error do not
auto-restart. Disabled tasks still require operator attention.

Validation: isolated focused suite 29 passed; full Python suite 561 passed and
6 subtests passed. A content-identical production ledger persistence test
succeeded with 151 closed Paper trades, zero open positions, and identical
SHA-256 before/after. Recovery must only re-enable the Paper scheduled task
after a verified backup and a no-op atomic persistence test. Keep real broker
execution disabled, and do not interpret a fresh monitor log alone as health.
