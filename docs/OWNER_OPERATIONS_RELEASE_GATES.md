# ATLAS Private Operations Evidence / Release Gate

This increment extends the existing authenticated FastAPI owner dashboard at `/sam`. It is **not** a separate published ChatGPT Sites deployment. It adds two sections to the Arabic-default, mobile RTL, bilingual dashboard: Evidence audit and Release readiness.

## Sources and read boundary
- Windows PAPER signed snapshot: the existing `/sam/api/snapshot` endpoint validates HMAC and returns allowlisted data.
- Evidence audit: deterministic, server-computed flags for duplicate/missing decision identifiers, missing snapshot provenance, missing outcome, absent Council votes and risk-veto/action conflicts.
- Release validation: optional allowlisted fields from a **signed** `release_validation` section. No unverified GitHub or Windows status is synthesized.
- The existing Windows exporter does not yet produce `release_validation`. This deliberately leaves readiness BLOCKED until a trusted, audited evidence collector is implemented and verified.

## Release gate
The gate requires: fresh signed snapshot, non-empty and clean decision evidence, verified Windows runtime, ledger production readback PASS, PR #103 focused tests PASS, CI PASS and Issue #82 CLOSED. Even when all are true, the label is REVIEW_REQUIRED, not APPROVED: owner signoff and release/deployment validations remain necessary.

## Known blockers as of branch creation
- PR #103 remains draft, pending tests and verification against real Council journals.
- Issue #82 remains open: Windows ledger atomic persistence needs production readback evidence.
- The ChatGPT Sites source, deployment, and owner authentication have **not** been verified. Do not publish signed owner telemetry via a public static site.
- Training before/after values remain unavailable unless separately signed and verified; no trading effectiveness is inferred.

## Validation
```bash
python -m pytest -q tests/test_owner_operations_gates.py tests/test_owner_dashboard.py
python -m pytest -q
```
Then check 401 unauthenticated, 503 unconfigured, Arabic RTL on mobile, English switch, Refresh/History, table sort/filter, stale snapshot, invalid signature and no broker-execution routes.

Safety boundary: `ATLAS_LIVE_TRADING=false`, `ATLAS_DASHBOARD_ONLY=true`. No trading settings, training, broker adapters, ledger contents or scheduled tasks are changed.
