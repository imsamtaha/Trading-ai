# ATLAS Operations Manager (PAPER-only)

## Purpose and authority
Read-only evidence validation, PAPER health reporting and release hygiene.
The manager cannot place broker orders, change risk policies, restart MT5, start
trading, deploy or merge. All real-money execution must remain disabled.

## Supported input formats
- **Canonical decision JSONL**: `decision_id`, `timestamp`, nonempty
  `votes` (agent, direction, timestamp, reason), `risk.veto` (boolean),
  `outcome.opened` (boolean).
- **Historical Council training JSONL**: `snapshot_id`, `timestamp`,
  `opinions` (agent, decision, confidence), `realized_direction`,
  `execution_environment`, `broker_execution_allowed`. This cannot
  establish independent risk vetoes, vote provenance, or execution outcomes.

An optional *independently sourced* canonical decisions file may supply
`source_snapshot_id` for a strict join to the legacy snapshots. Neither the
auditor nor the operations manager manufactures missing IDs, reasons, votes,
risk vetoes or outcomes. A schema PASS is not live runtime approval.

## Private manual verification in an isolated working copy
```powershell
$env:ATLAS_LIVE_TRADING = 'false'
$env:ATLAS_REAL_MONEY_EXECUTION = 'false'
$env:MT5_REQUIRE_DEMO = 'true'

python -m pytest -q tests/test_audit_paper_evidence.py tests/test_audit_legacy_council_evidence.py tests/test_atlas_ops_manager.py tests/test_atlas_ops_legacy.py
python -m pytest -q

python -m scripts.atlas_ops_manager 'C:\private\atlas_council_training.jsonl' --journal-format legacy
python -m scripts.audit_legacy_council_evidence 'C:\private\atlas_council_training.jsonl'
python -m scripts.atlas_ops_manager 'C:\private\canonical_decisions.jsonl'
```

If an independent private canonical file exists, add
`--canonical-decisions 'C:\private\canonical_decisions.jsonl'` to either
legacy invocation. Do not copy private journal content, account IDs or secrets
into GitHub comments or CI logs.

Exit codes: 0 = schema PASS, 1 = evidence FAIL (standalone auditor),
2 = UNVERIFIED / blocked (or invalid CLI). `--output` in the canonical
auditor only creates a new report and refuses to overwrite any existing path.

## Verified real-data result (2026-11-01)
On an authorized Windows host, 674 well-formed legacy Council records were
inspected read-only. All had nonempty unique snapshot IDs, agent opinions and
`broker_execution_allowed=false`; none contained independent decision IDs,
veto outcomes or full vote provenance. The new legacy auditor returned
`UNVERIFIED` (exit code 2), correctly preventing false PASS.

**Windows PAPER is independently blocked.** The recent private health report
showed `paper=HEARTBEAT_UNAVAILABLE`, stale Council/Shadow/ledger state,
`mt5=ALGO_DISABLED`, and tunnel/public-route unavailable. The log showed
MT5 IPC timeout (-10005) and intermittent Supabase TLS/read timeouts.
A read-only connectivity check successfully resolved the configured Supabase
host, connected to TCP/443 and received an unauthenticated HTTP 401, which
**does not** prove the application's authenticated PATCH succeeds.

Read `docs/ATLAS_PAPER_RECOVERY_RUNBOOK.md` before any controlled recovery.
The manager's environment flag check is **not** a direct attestation of the
running production process.

## Release blockers
1. Full current-head hosted Linux/Windows CI plus focused local tests must PASS.
2. Document/resolve MT5 IPC failures and Supabase audit durability; confirm
   at least two fresh heartbeat samples and current durable Paper state.
3. Obtain a separate canonical decision/vote/veto/outcome source; prove joins
   and missingness fail closed. Never infer these from historical opinions.
4. Independently verify PAPER-only, `ATLAS_LIVE_TRADING=false` and no
   broker execution in the actual runtime; preserve existing work.
5. Review current PR changes, CodeRabbit findings, owner/mobile state as
   applicable. Leave PR #103 in DRAFT until all release gates pass.

No claim is made about profitability, out-of-sample validity, or live readiness.
