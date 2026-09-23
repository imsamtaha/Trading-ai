# ATLAS Full Test Orchestrator

Run the Windows-first validation suite from the repository root:

```powershell
.\scripts\run_full_atlas_test.ps1
```

Optional switches:

```powershell
.\scripts\run_full_atlas_test.ps1 -SkipDocker
.\scripts\run_full_atlas_test.ps1 -SkipWeb
.\scripts\run_full_atlas_test.ps1 -SkipMT5
.\scripts\run_full_atlas_test.ps1 -OutputDir artifacts
```

The runner always forces `ATLAS_LIVE_TRADING=false` and `MT5_REQUIRE_DEMO=true`. It never places a real-money order.

## Test groups

- `repo_tests` — complete Python suite.
- `web_tests` — JavaScript syntax, demo/auth tests, and website build.
- `risk_safety` — deterministic risk, execution-gate, paper-gate, and demo-account safety tests.
- `windows_integrity` — Windows journal/status integrity plus deployment-script parsing.
- `api_smoke` — Docker build, `/health` 200, and protected `/mt5/test-order` 403.
- `mt5_demo_runtime` — conditional Windows MT5 demo connection and one safe forward-demo cycle.
- `restart_reconnect` — deterministic duplicate/reconnect validation when a focused contract exists; otherwise the report remains PARTIAL.

## Result semantics

`PASS` means every executed group passed and no prerequisite was missing. `PARTIAL` means the repository checks are healthy but an optional runtime prerequisite or deterministic contract was unavailable. `FAIL` means at least one executed validation failed; safety failures always produce FAIL.

Reports are written to:

- `artifacts/ATLAS_TEST_REPORT.json`
- `artifacts/ATLAS_TEST_REPORT.md`
- `artifacts/logs/`

Secret-like keys containing `KEY`, `TOKEN`, `SECRET`, `PASSWORD`, or `CREDENTIAL` are recursively redacted by the report renderer.

## MT5 requirements

For the MT5 stage, use Windows with the MetaTrader5 Python package, an open MT5 terminal, and the existing `.env` connection settings. The broker adapter is required to confirm a DEMO account because `MT5_REQUIRE_DEMO=true`; a live account is rejected rather than downgraded to a warning.

The current `run_atlas_mt5.py --once` path records only paper/demo activity and never sends a broker order.
