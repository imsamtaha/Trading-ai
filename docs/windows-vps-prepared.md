# ATLAS Windows VPS source package — not activated
This package is a local preparation snapshot. No VPS was purchased, provisioned, connected, or enabled.
It contains three versioned source ZIPs (frontend, private backend, council), SHA-256 checksums, and source commit IDs.
Do not run the existing installation or trading launcher scripts on a target yet: they contain paths tied to the current Windows host.
No real .env, terminal token, broker login password, production database, runtime switch, daily counter, or learning state is intentionally included.
Secrets and changing state must be transferred privately only at an approved cutover. Existing Demo activity continues on the original Windows host.

## Target preparation before activation
1. Provide a full Windows VPS with a licensed OS, dedicated Windows user, RDP access, and sufficient resources. Initial capacity estimate: 4 vCPU, 8 GB RAM, 80 GB SSD; validate usage.
2. Extract each source ZIP into a separate versioned directory. Install compatible Python and Node dependencies using repository instructions, without launching trading jobs.
3. Install the correct FxPro MT5 terminal and prepare its dedicated owner Demo account. Do not share this terminal with customer agents.
4. Adapt all absolute launcher, worker, supervisor and account paths to the target. Keep REAL execution false and Demo council switches false on the target.
5. Prepare frontend/backend/supervisor/council task definitions in a DISABLED state. This source package does not register tasks.
6. Build the frontend into its own new directory and run offline tests. Review protected configuration, logs, firewall and access. Public route remains on the old host.
7. Test restart and RDP disconnect handling before cutover. No test trade or target trading activation is authorized by preparing this package.

## Later cutover, requiring a separate activation instruction
Stop the old council first; reconcile all broker positions and any unknown order result.
Copy final daily counts, learning records, audit database and runtime state after the old worker stops; preserve their values.
Verify login/server/Demo mode, max 3 total open positions and 10 entry attempts per UTC day.
Switch the public route and start a single target execution worker only when activation is explicitly authorized.
Keep the original installation inactive as rollback. Never let both workers trade the same account simultaneously.

## Verifying the package
Check each source ZIP hash against manifest.json with Get-FileHash -Algorithm SHA256.
The manifest must read PREPARED_NOT_ACTIVATED, with server_provisioned, tasks_registered, and trading_enabled_on_target all false.
Hashes verify integrity of this snapshot; they do not certify a deployed server or a working target configuration.

