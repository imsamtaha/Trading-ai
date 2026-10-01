# ATLAS resilient Windows server design

Status: Design proposal; no cloud server has been provisioned or migrated.
Purpose: Keep the ATLAS connection page, owner Demo council, and FxPro MT5 operational without depending on the owner's home PC or home internet.
Scope: Owner Demo trading first. Customer execution and real-money automation remain separate future work; payment alone must not unlock real-money execution.

## Selected architecture
Use one always-on full Windows VPS for the initial owner deployment. A provisional starting size is 4 vCPU, 8 GB RAM, and 80 GB SSD; validate actual CPU/RAM/IO use before choosing a paid plan. These are planning estimates, not guaranteed minimums or availability promises.
Run the existing Next.js frontend and FastAPI backend on loopback-only ports 8011 and 8012. Publish the existing domain through a supervised Cloudflare Tunnel. Keep one configured tunnel supervisor per server; audit existing service/task duplicates before migration.
Run the council Python worker and its reserved FxPro Demo MT5 terminal under the same dedicated Windows account and compatible Windows session. Terminal startup and Python IPC must be tested after a real reboot and an RDP disconnect before release. Do not store an auto-login password in a script.
Keep customer connections on separate MT5 installations and separate agent processes. No request may change the terminal reserved for the owner council.

## Alternatives considered
1. Full Windows VPS: preferred for this Python/Node/MT5 stack; independent of the home device, but adds hosting cost and remains a single-host failure domain initially.
2. Existing PC plus UPS and backup LTE/5G router: lower migration effort, but still depends on local power, hardware, and ISP routing. A software server cannot create internet connectivity during a physical outage.
3. Two Windows hosts with standby failover: stronger recovery, but more cost and coordination. Defer until a durable execution lease and broker reconciliation are proven; two active workers could duplicate trades.

## Components and boundaries
- Public frontend: connection, subscription, and council status views; no direct broker calls.
- Private API: authentication, verified subscription entitlements, runtime controls, and account-scoped telemetry.
- Owner execution agent: sole writer of owner Demo orders; explicit terminal path, login/server validation, and MT5 Demo mode verification before every order.
- MT5 terminal: broker connection and broker-confirmed positions/history; existing SL/TP remain at the broker when the app is unavailable.
- Supervisor: checks liveness and readiness, then restarts only the failed component with bounded backoff. It never sends a test order.
- Persistent state: daily entry counts, learning ledger, execution audit, runtime switches, and recovery journal on a persistent data disk, outside TEMP.
- External monitor: checks HTTPS from outside the VPS, so a healthy localhost is not mistaken for a healthy public route.

## Recovery behaviour
Probe every 30 seconds. Distinguish PROCESS_DOWN, API_NOT_READY, PUBLIC_ROUTE_DOWN, MT5_OFFLINE, AUTH_REQUIRED, ALGO_DISABLED, and HEALTHY; surface the actual reason to the user instead of reporting all failures as signed out.
After three consecutive application failures, restart only that application, with 30/60/120-second retry delays and a 5-minute cooldown after repeated failures. No restart loops and no blanket reboots during an order submission.
For MT5 network interruptions, pause new entries and retry the saved expected Demo session with bounded backoff. Do not guess credentials, switch to a different account, or silently turn off safety checks. Authentication failures require an authenticated user to reconnect.
After recovery, verify account identity, Demo mode, quote freshness, trading permissions, open positions, outstanding order outcomes, and daily counters before resuming.
If the VPS network fails, pause execution; provider network recovery or standby failover supplies availability, not a local retry loop. Phone/home internet loss must not stop the hosted agent.
Display the most recent successful heartbeat timestamp, a specific connection state, and a retry control. Cache only the public offline contact page; never show cached account state as live.

## Trading and duplicate prevention
Owner policy: at most 3 total open positions on the expected Demo account, at most 10 attempted entries per UTC day, 0.01 lots per entry, existing per-trade cash-risk check and daily 3% equity-loss stop. The scheduler remains every 30 minutes; 3 is a ceiling, not a target to fill.
Keep the runtime count gate and the immediate pre-send broker count gate. Include existing SL risk in the council snapshot. If position data or protective-stop risk is unavailable, block new entries.
Use a durable transactional execution journal with a unique request ID and a single account lease. Mark an attempt before calling MT5. An interrupted or ambiguous order submission becomes UNKNOWN and is reconciled against broker history before any retry. This journal/lease upgrade is proposed, not currently deployed.
Daily counts and learning state must survive restarts and deployment changes. Do not reset them to bypass limits. Standby promotion must revoke/expire the primary lease before order execution can resume.

## Deployment and backups
Stage releases into a new directory, build and test before switching the active launcher, then check both localhost and external HTTPS. Keep the previous release for rollback; never rebuild the directory actively serving users.
Move runtime switches from TEMP to an explicit persistent path shared by the API and agent, and copy existing daily/learning/audit state during migration. Validate write permissions under the dedicated user.
Take daily encrypted state backups outside the host, and test restoration on a non-trading staging instance. Secrets belong in protected server configuration or a secret store, not Git or logs.
Start with daily recovery backups; target recovery time <=15 minutes for a host rebuild and an app recovery <=2 minutes when the host/network remain healthy. These are acceptance targets, not tested guarantees. Do not promise zero downtime or zero data loss.

## Acceptance checks before cloud cutover
- Killing the frontend/backend/tunnel recovers the affected component without duplicate council workers.
- A VPS reboot and RDP disconnect preserve the correct MT5 account and allow the agent to resume under the configured Windows session model.
- A simulated network outage pauses entries; recovery reconciles outstanding requests without duplicates.
- 0/1/2 existing positions permit evaluation; 3 or more block an additional entry, including positions opened outside ATLAS.
- The eleventh daily entry attempt is blocked; counters, open-position risk, and learning records survive restart.
- A customer connection cannot change the council terminal/account. REAL execution remains locked.
- An external browser loads /connect and completes an authenticated owner connection-state check; HTTP 200 alone is insufficient.

## Migration sequence
1. Select/provide a Windows VPS and verify access, resources, licensing, network, and compatible MT5 execution session.
2. Deploy signed-off code and protected configuration; validate Demo connectivity and all recovery tests with the old worker stopped.
3. Move persistent state and update the existing tunnel/origin routing in one controlled cutover.
4. Enable one Demo worker only, verify account identity and limits, and observe at least a full restart/reconnection test cycle.
5. Retain the home installation as an inactive fallback. It must not trade simultaneously with the VPS.

## Dependencies for execution
A chosen VPS/hosting account and approved budget are required before provisioning. No purchase, subscription, DNS change, cloud deployment, or live-account activation is performed by this design document.

## Official references
- MT5 Python initialize: https://www.mql5.com/en/docs/python_metatrader5/mt5initialize_py
- MT5 virtual hosting migration restrictions: https://www.metatrader5.com/en/terminal/help/virtual_hosting/virtual_hosting_migration
- Windows VM disaster recovery: https://learn.microsoft.com/en-us/azure/virtual-machines/windows/tutorial-disaster-recovery
