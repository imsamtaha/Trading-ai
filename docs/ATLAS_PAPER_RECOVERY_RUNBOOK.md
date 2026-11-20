# ATLAS PAPER recovery and evidence gates — 2026-11-01

**Status: RELEASE BLOCKED.** This is a read-only operations runbook, not approval to start, restart, merge, or place orders.

## Verified Windows observations (owner device Sam)
- `ATLAS Paper Monitor` is marked Running, but the private health report declares `paper=HEARTBEAT_UNAVAILABLE`.
- `backend=HEALTHY`, `frontend=HEALTHY`, `tunnel=HTTP_UNAVAILABLE`, `public_route=HTTPS_UNAVAILABLE`, `mt5=ALGO_DISABLED`. HTTP 200 from an API does **not** make the PAPER engine healthy.
- The latest paper log includes `MT5 initialize failed: (-10005, 'IPC timeout')` and repeated Supabase audit TLS/read timeouts. These are two distinct failure signals. The log was already stale when inspected.
- Two MT5 terminal executables were observed, one FxPro and one MetaTrader 5; this is **not sufficient evidence** to terminate either terminal or blame a specific process.
- Shadow report, Council profile, training JSONL, and PAPER ledger are stale. No synthetic event, fresh timestamp, or fabricated outcome may be written to make health look green.
- The PAPER launcher in the *local* Windows workspace explicitly sets `ATLAS_LIVE_TRADING=false`, `ATLAS_REAL_MONEY_EXECUTION=false`, `ATLAS_DEMO_ORDER_EXECUTION=false`, `MT5_REQUIRE_DEMO=true`. This does not prove every currently running process inherited them.
- Do not reset or overwrite unrelated local modifications. Do not restart a Running Paper task: the current watchdog is intentionally designed to avoid duplicate workers.

## Real Council schema findings
- The current historical file is `ATLAS/.runtime/paper/atlas_council_training.jsonl`, 674 valid JSONL rows at time of inspection.
- Its fields are `timestamp`, `snapshot_id`, `realized_direction`, `opinions`, `execution_environment`, `broker_execution_allowed`.
- 674 records have unique, nonblank snapshot IDs and agent opinion identities, with no observed `broker_execution_allowed=true`. They **do not** include a separately verifiable `decision_id`, `risk.veto`, `outcome.opened`, or fully proven vote provenance.
- Run the new **read-only** compatibility audit:
```powershell
$env:ATLAS_LIVE_TRADING = 'false'
python -m scripts.audit_legacy_council_evidence 'C:\private\atlas_council_training.jsonl'
```
Exit 2 (`UNVERIFIED`) is the expected conservative result without an independently sourced canonical decisions journal. The tool does not infer missing fields from `realized_direction` or `opinions`. With a verified separate canonical source, pass `--canonical-decisions <private-jsonl-path>` for joins using explicit `source_snapshot_id`.

## Safe recovery checklist (execution owner, Windows)
1. Validate the FxPro DEMO session/terminal responsiveness and IPC state without stopping either MT5 terminal or starting a second Paper worker. If IPC is unhealthy, investigate terminal access, active session, and duplicate initializations first.
2. Independently check DNS, TLS, proxy/firewall and network reachability to the configured Supabase endpoint. Do **not** print or upload API credentials, credentials files, host identifiers, or private journal records.
3. Inspect the actual Paper process environment and broker-write guard before authorizing any controlled restart. If access is inconclusive, remain **BLOCKED**.
4. After an *authorized, controlled* safe recovery, require at least two consecutive fresh Paper heartbeat samples and a current durable Paper ledger. A freshly edited logfile alone is not a substitute.
5. Require fresh Shadow report and Council evidence joins. Match unique snapshot IDs to independent decision IDs, vote provenance, risk veto and **actual** outcomes. A legacy journal alone is insufficient.
6. Re-run focused tests, the entire repository suite on Windows/Linux CI, independent CodeRabbit review, and authenticated owner checks prior to merging PR #103.

## Code validation
- `python -m pytest -q tests/test_audit_paper_evidence.py tests/test_atlas_ops_manager.py tests/test_audit_legacy_council_evidence.py`
- This validation is only of code; it cannot establish production runtime health, profitability or execution readiness.
- Do not change the risk veto policy or enable broker execution. Remain `PAPER-only` and `ATLAS_LIVE_TRADING=false`.
