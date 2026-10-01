# Windows stability supervisor
Installed on the existing Windows host; this is not a cloud VPS.
Run scripts/install-windows-supervisor.ps1 under the same Windows user as MT5 and the existing ATLAS tasks.
The ATLAS Windows Supervisor task starts at user logon and is retriggered each minute if it exits; IgnoreNew plus a file lock prevent concurrent supervisors.
It probes backend, frontend, public HTTPS, and the reserved owner Demo MT5 terminal every 30 seconds. Slow network probes can lengthen that interval.
After three failed local HTTP probes, it starts a Ready scheduled task, with 30/60/120/300-second recovery backoff.
A Running-but-unhealthy task is reported for attention rather than killed: Task Scheduler may not own orphaned child processes and execution can be in flight.
MT5 is observed through an isolated subprocess with a timeout; no orders, test trades, account switching, or algorithmic permission changes are issued.
Cloudflare and home internet failures are reported; the supervisor does not reset the router, alter DNS, or promise continuity without a backup connection.
State is at the current user's ATLAS_Backup/server: status.json, recovery-state.json, and bounded events.jsonl plus one rotated log.
Only sanitized status is returned through the authenticated owner /api/runtime/status endpoint.
The dashboard displays monitor age and per-component health; after 180 seconds, data is marked stale rather than live.
The Windows user must be logged in and the computer powered on. Independent home-network availability requires VPS migration or backup LTE/5G and power.
Demo policy remains maximum 3 total open positions and 10 entry attempts per UTC day; REAL stays locked.
To stop monitoring: Stop-ScheduledTask -TaskName 'ATLAS Windows Supervisor'; Disable-ScheduledTask -TaskName 'ATLAS Windows Supervisor'.
To resume: Enable-ScheduledTask -TaskName 'ATLAS Windows Supervisor'; Start-ScheduledTask -TaskName 'ATLAS Windows Supervisor'.
