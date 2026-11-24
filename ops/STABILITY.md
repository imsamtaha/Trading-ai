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

Historical validation recorded on 2026-10-10: isolated focused suite 29 passed; full Python suite 561 passed and
6 subtests passed. A content-identical production ledger persistence test
succeeded with 151 closed Paper trades, zero open positions, and identical
SHA-256 before/after. Recovery must only re-enable the Paper scheduled task
after a verified backup and a no-op atomic persistence test. Keep real broker
execution disabled, and do not interpret a fresh monitor log alone as health.

## 2026-11-02 PR #81 persistence repair

The published repair is scoped to issue #82 and retains the PR's original
ceilings of five open Paper positions and 100 daily entries. It recovers the
persistence and supervisor changes from local commit `535bb11`, with additional
coverage for Windows readers in a second process, log rotation, malformed newer
ledgers, and partial native replacement failures.

Each write flushes and fsyncs a unique temporary file before replacement.
After six bounded `Path.replace` attempts, Windows can use `ReplaceFileW` with
an original-file backup at `<ledger>.replacement.bak`. Successful replacement
removes that backup. A partial replacement, interrupted cleanup, or process
crash that leaves the backup causes subsequent ledger loads to fail closed;
the backup must never be overwritten by an automatic retry. Failed temporary
files are removed when the filesystem permits it, and are never settled trades.
The supervisor reports `LEDGER_PERSISTENCE_FAILED` while a recovery backup exists
or a recorded persistence failure lacks a newer readable ledger with valid
trade collections. Disabled tasks remain disabled, and storage faults suppress
automatic starts without resetting the existing recovery budget.

Windows can leave the original file under its backup name on some replacement
errors; see [Microsoft's ReplaceFileW failure semantics](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-replacefilew).
The backup interlock prevents that missing canonical path from being mistaken
for a new empty ledger.

Recovery procedure (operator controlled):

1. Keep the Paper Monitor stopped/disabled during storage repair. Identify its
   actual task action, ledger path and supervisor state directory. Keep broker
   execution disabled; do not broaden ACLs or alter trading limits.
2. Before any production write, copy the exact canonical ledger to a separate
   restricted recovery location. Record and compare SHA-256, byte count, and
   open/closed counts. If `.replacement.bak` exists, preserve it separately;
   inspect both versions and reconcile provenance before choosing one. Never
   replace the canonical ledger with an arbitrary `.tmp` file.
3. Diagnose file attributes, streams, Defender events and open handles with
   Windows Restart Manager or approved handle tools. First reproduce and test
   replacement on a disposable isolated ledger. A lock that denies delete
   sharing still requires releasing the owning reader; repeated restarts will
   not repair it.
4. If a partial native replacement left only the verified original backup,
   restore it atomically to the canonical name while the writer is stopped.
   If both files exist, preserve both externally, verify the chosen canonical
   data, then archive the interlock backup. Never clear it blindly.
5. With an exact external snapshot preserved, load the production ledger under
   its writer lock and perform a content-identical persist. Verify readback,
   SHA-256, counts and absence of temporary/recovery files. If canonical bytes
   are not already in the writer's format, investigate that difference before
   declaring a byte-identical verification passed.
6. Only after persistence is verified should the operator re-enable/start the
   Paper Monitor and observe repeated successful writes with no new errors.
   Confirm the supervisor clears the failure after a newer valid ledger, not
   merely a Running task or recent log timestamp.

The 2026-11-02 PR work uses isolated test ledgers. It does not redeploy services,
change scheduled tasks, or repeat the historical production recovery drill.
Local Windows validation passed 568 Python tests and 6 subtests, including the
real second-process sharing tests and simulated partial-replacement failure.
The regression run against the old PR code failed 12 checks before the repair.
`git diff --check` also passed. Hosted CI and current production persistence
monitoring remain separate release gates.
