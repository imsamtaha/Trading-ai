# ATLAS Full Test Orchestrator — Design

## Goal
Build one coordinated test harness for ATLAS that validates the repository, API, web layer, risk controls, Windows integrity checks, MT5 demo connectivity, and one end-to-end demo execution cycle, then emits a single PASS / PARTIAL / FAIL report.

## Scope
The orchestrator covers:
- Python unit and integration tests.
- Risk and execution-gate tests.
- Dashboard/API health checks.
- Docker / Cloud Run smoke validation.
- Web JavaScript and public-site validation.
- Windows journal and demo-status integrity.
- FxPro / MT5 demo account verification when the Windows host is reachable.
- Fresh quote-feed verification.
- One demo/simulated ATLAS cycle from market data through decision, risk evaluation, ledger, and audit output.
- Restart/reconnect duplicate-protection checks where supported by the existing runtime.
- Consolidated machine-readable and human-readable reports.

## Explicit Safety Boundary
The orchestrator must never enable real-money execution.
- `ATLAS_LIVE_TRADING` remains `false`.
- `MT5_REQUIRE_DEMO` remains `true` for MT5 runtime validation.
- Any broker or execution test is limited to demo/simulated paths already intended for safe validation.
- A failed safety assertion forces overall status to FAIL.
- The test harness must not modify account credentials or place real-money orders.

## Architecture
Use a Windows-first PowerShell orchestrator because the MetaTrader5 package and the real terminal bridge require Windows. The script will run local validation groups, call existing Python/Node test commands, probe the FastAPI service, and conditionally run MT5 demo checks when the terminal and credentials are available.

The orchestrator will write results into a small structured report model. Each test group records status, duration, command, and a concise failure reason. A Markdown report is generated from the same result object so there is one source of truth.

GitHub Actions remains the always-on CI layer. It will continue running repository-safe checks on hosted runners, while the Windows orchestrator is the authoritative end-to-end demo-runtime check on the connected desktop.

## Proposed Files
- `scripts/run_full_atlas_test.ps1` — top-level Windows orchestrator.
- `scripts/atlas_test_report.py` — report aggregation and JSON/Markdown rendering helper.
- `tests/test_atlas_test_report.py` — report-model tests.
- `tests/test_full_test_orchestrator_contract.py` — static/contract tests that assert required safety flags and required test groups exist in the PowerShell runner.
- `docs/ATLAS_FULL_TEST.md` — operator usage and result interpretation.
- `.github/workflows/tests.yml` — optionally add a non-MT5 contract check for the orchestrator so CI prevents accidental drift.

## Test Groups
1. `repo_tests`
   - Run `python -m pytest -q`.
   - Expected: zero failed tests.

2. `web_tests`
   - `node --check web/assets/site.js`.
   - `node --test tests/test_demo_model.cjs`.
   - `node --test tests/test_google_auth.mjs`.
   - `node --check web/assets/google-auth.js`.
   - `python scripts/build_website.py`.

3. `risk_safety`
   - Assert `ATLAS_LIVE_TRADING=false`.
   - Assert `MT5_REQUIRE_DEMO=true` for MT5 stage.
   - Re-run focused gate / journal / risk tests.
   - Fail if any live-money setting is enabled.

4. `api_smoke`
   - Start or probe the API in dashboard/demo-safe mode.
   - `/health` must return HTTP 200 and healthy state.
   - `/mt5/test-order` must remain blocked under the safe test configuration.

5. `windows_integrity`
   - Parse `scripts/deploy_google_cloud.ps1`.
   - Run journal-integrity and demo-status integrity tests.

6. `mt5_demo_runtime`
   - Only runs when Windows host, MetaTrader5 package, terminal, and required demo credentials are available.
   - Verify MT5 initializes.
   - Verify account trade mode is DEMO.
   - Verify server/login match configured demo expectations when configured.
   - Verify account info and at least one configured symbol quote can be read.
   - Verify quote timestamp is fresh enough for the existing stale-data policy.
   - Run a single existing ATLAS demo/paper cycle, not a live-money order.
   - Verify expected ledger / journal artifacts or status output are produced.

7. `restart_reconnect`
   - Validate idempotent restart/reconnect behavior using existing testable interfaces.
   - If the current codebase lacks a safe automated restart contract, mark this group PARTIAL with the exact missing prerequisite instead of pretending it passed.

## Overall Status Rules
- `PASS`: every required local group passes and MT5 demo-runtime passes when the Windows demo environment is available.
- `PARTIAL`: repository/CI groups pass but the MT5 demo environment is unavailable or a runtime prerequisite is missing.
- `FAIL`: any test fails, any safety assertion fails, API health fails, or a real-money execution flag is detected.

## Reporting
Write both:
- `artifacts/ATLAS_TEST_REPORT.json`
- `artifacts/ATLAS_TEST_REPORT.md`

The report includes:
- timestamp
- git commit SHA
- environment summary with secrets omitted
- overall result
- per-group status and duration
- concise failure reasons
- next required action

No credentials, API keys, passwords, MT5 passwords, or raw secret environment variables may be written to reports.

## Success Criteria
- Existing CI remains green.
- The orchestrator can be launched with one PowerShell command.
- Failure in any required safety condition produces non-zero exit status.
- Reports are deterministic and redact secrets.
- MT5 demo checks clearly distinguish DEMO from LIVE accounts.
- Real-money execution remains disabled throughout the test process.
- The operator receives one final summary rather than verbose narration of each command.

## Out of Scope
- Enabling real-money trading.
- Removing execution safety gates.
- Adding or storing real-account credentials.
- Placing a real-money micro-lot order.
- Automatically promoting demo readiness to live-money readiness.
