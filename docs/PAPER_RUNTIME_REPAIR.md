# Paper runtime repair

This patch addresses worker ownership and operational observability only.
It does not change trade-entry logic, risk limits, ledger contents, training,
or broker execution. It does not claim to repair the machine-specific
RECOVERY_EXHAUSTED status: that recovery agent is absent from this repository.

## Before rollout

Stop the existing manual/scheduled paper worker once. Older workers do not
participate in the new lifetime lock. Do not launch an extra worker alongside
them. Back up the project and runtime data. Keep the current environment and
ledger path; never substitute an empty ledger to get the worker to start.

The inspected repository caps paper positions at 5 and daily entries at 15.
The supplied October 13 report describes 10 and 150. This indicates a different
local revision/configuration. Do not deploy over that local revision without
comparing changes. This patch does not alter or bypass those caps.

## Windows launch

Use the project's existing Python environment with its installed dependencies:

```powershell
& .\ops\run-atlas-paper-monitor.ps1 -ProjectPath $ProjectPath -PythonPath "$ProjectPath\.venv\Scripts\python.exe"
```

Set the existing Task Scheduler action to this wrapper only after comparing the
local revision. Use the actual project path, not an assumed ATLAS-TEST folder.
No task registration, restart, broker connection, or deployment was performed
by authoring this patch. PowerShell/MT5 must be validated on Windows.

## Observable behavior

- A second patched runner using the same canonical ledger exits with code 3
  before constructing a monitor or connecting to MT5. Crashes release the OS lock.
- `<ledger>.health.json` records UTC time, PID and cycle state. Check freshness
  against cycle duration; CYCLE_STARTED alone does not mean a completed cycle.
- `<ledger>.monitor.log` stores operational summaries, rotating at 5 MiB with
  five backups. Full signal/training evidence remains in its existing journal.
- Normal cycles no longer dump full candle arrays to redirected stdout.
- Existing large logs are retained. This patch neither truncates an active log
  nor deletes historical evidence. Signal journal archival remains separate work.
- Unexpected failures retain nonzero process status and an exception log. MT5
  connection failures retain the existing retry behavior and failed health state.

After rollout verify one worker, recent completed-cycle health, log timestamps,
and no broker orders. Restart Windows separately to validate task continuity.
Shadow/recovery report refresh and bid/ask quality instrumentation remain pending.
