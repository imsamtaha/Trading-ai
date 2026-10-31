# ATLAS Operations Manager (PAPER-only)

## Purpose
Operations manager for **evidence integrity and release hygiene**, not a trading executor.
This PR introduces a one-shot, read-only PAPER journal gate in
`scripts/atlas_ops_manager.py` and a fail-closed auditor in
`scripts/audit_paper_evidence.py`.

## Authority and prohibitions
- Allowed: inspect an *exported, private* JSONL journal, detect incomplete or contradictory evidence, propose safe repairs, and report whether tests / real schema verification are still pending.
- Prohibited: submitting broker orders, changing risk limits or vetoes, starting/stopping MT5, manipulating credentials, switching to live, merging PRs or deploying production without separate release gates.
- Set `ATLAS_LIVE_TRADING=false` explicitly for test sessions; a missing or true value blocks the operations-manager gate. This check only reads the process environment and **does not attest the production runtime**.
- Do not copy private Council records into PR comments, GitHub Actions logs or public reports.

## Manual invocation (isolated working copy)
```powershell
$env:ATLAS_LIVE_TRADING = 'false'
python -m pytest -q tests/test_audit_paper_evidence.py tests/test_atlas_ops_manager.py
python -m pytest -q
python -m scripts.atlas_ops_manager 'C:\private\paper-council-export.jsonl'
python -m scripts.audit_paper_evidence 'C:\private\paper-council-export.jsonl'
```

The input schema is `decision_id` (nonblank string), `timestamp` (nonblank string),
nonempty `votes` (each with nonblank `agent`, `direction`, `timestamp`, `reason`),
`risk.veto` (boolean), and `outcome.opened` (boolean).

The auditor has no input mutations. It prints to stdout by default. An optional
`--output` **creates** a new file, refusing to overwrite any existing file or link.
Exit codes: 0 for schema PASS, 1 for contradictory/invalid evidence FAIL, 2 for
UNVERIFIED or CLI errors. The operations manager exits 2 when either evidence
or the explicit safety environment flag is not verified.

## Release gates
1. Review and pass focused tests plus the full repository suite on the PR head.
2. Restore hosted Linux/Windows/GitHub Actions CI (Issue #88) and inspect the actual job results.
3. Verify the export schema against real Council journals, provenance join keys,
   risk vetoes, and outcomes. Missing evidence MUST NOT be interpreted as success.
4. Validate Windows/MT5 in a separately authorized, read-only session. Ensure
   `ATLAS_LIVE_TRADING=false` in the **actual** runtime, not just a test shell.
5. Request manual CodeRabbit review; resolve substantive findings.
6. Keep PR as DRAFT, do not merge until all checks are met.

## Operator reporting
Use statuses `PASS`, `FAIL`, `UNVERIFIED`. A schema PASS means
**PAPER_SCHEMA_CHECK_ONLY** and must never be presented as permission to launch
live trading. The ChatGPT ATLAS operations watch can monitor remote GitHub PR/CI
and highlight blockers; it is separate from running this local script.

## Out of scope
No claims about profitability, OOS validation, Kenji/Nova strategy fixes,
correctness of agent decisions, or availability of real trading runtime.
