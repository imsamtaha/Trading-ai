# ATLAS Full Test Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a one-command Windows-first ATLAS test orchestrator that validates repository, web/API, safety gates, Windows integrity, and conditional MT5 demo runtime, then emits PASS/PARTIAL/FAIL reports.

**Architecture:** A PowerShell runner coordinates existing Python/Node checks and conditional MT5 demo validation. A small Python report helper owns deterministic JSON/Markdown output and redaction. GitHub Actions adds contract coverage so safety and test-group definitions cannot drift silently.

**Tech Stack:** PowerShell 7, Python 3.13, pytest, Node 22, FastAPI, Docker, MetaTrader5 on Windows demo environments, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-23-atlas-full-test-orchestrator-design.md`

## Global Constraints

- `ATLAS_LIVE_TRADING=false` throughout validation.
- `MT5_REQUIRE_DEMO=true` for MT5 runtime validation.
- Never place a real-money order.
- Never persist secrets into test reports.
- Overall FAIL on any safety assertion failure.
- Overall PARTIAL when repository checks pass but MT5 demo runtime cannot run because the Windows/demo environment is unavailable.

## Review Focus

- Missing MT5 package/terminal must yield PARTIAL, not PASS or crash.
- A LIVE account must hard-fail the MT5 stage.
- Secret-looking values must be redacted from JSON and Markdown reports.
- Stale quote data must fail or block the runtime stage according to existing stale-data policy.
- Restart/reconnect validation must never duplicate a simulated trade or claim success when no contract exists.

---

### Task 1: Report Model and Renderer

**Files:**
- Create: `scripts/atlas_test_report.py`
- Create: `tests/test_atlas_test_report.py`

**Interfaces:**
- Produces: `build_report(commit_sha: str, groups: list[dict]) -> dict`
- Produces: `write_report(report: dict, output_dir: str) -> tuple[str, str]`
- Produces: `redact(value: object) -> object`

- [ ] **Step 1: Write failing report tests**

```python
from scripts.atlas_test_report import build_report, redact


def test_report_is_partial_when_mt5_is_unavailable_but_required_checks_pass():
    groups = [
        {"name": "repo_tests", "status": "PASS", "required": True},
        {"name": "mt5_demo_runtime", "status": "NOT_RUN", "required": False, "reason": "desktop offline"},
    ]
    assert build_report("abc", groups)["overall"] == "PARTIAL"


def test_report_fails_on_safety_failure():
    groups = [{"name": "risk_safety", "status": "FAIL", "required": True}]
    assert build_report("abc", groups)["overall"] == "FAIL"


def test_redact_masks_secret_like_keys():
    assert redact({"MT5_PASSWORD": "secret", "status": "ok"}) == {"MT5_PASSWORD": "***REDACTED***", "status": "ok"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_atlas_test_report.py -q`
Expected: FAIL because `scripts.atlas_test_report` does not exist.

- [ ] **Step 3: Implement report helper**

Implement deterministic JSON/Markdown generation, status reduction, duration fields, timestamp, commit SHA, and recursive secret-key redaction for keys containing `KEY`, `TOKEN`, `SECRET`, `PASSWORD`, or `CREDENTIAL`.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_atlas_test_report.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/atlas_test_report.py tests/test_atlas_test_report.py
git commit -m "test: add ATLAS test report model"
```

### Task 2: Orchestrator Contract Tests

**Files:**
- Create: `tests/test_full_test_orchestrator_contract.py`
- Create: `scripts/run_full_atlas_test.ps1`

**Interfaces:**
- PowerShell entry point: `scripts/run_full_atlas_test.ps1`
- Parameters: `-SkipDocker`, `-SkipWeb`, `-SkipMT5`, `-OutputDir artifacts`

- [ ] **Step 1: Write failing contract tests**

```python
from pathlib import Path

SCRIPT = Path("scripts/run_full_atlas_test.ps1")


def test_orchestrator_hard_codes_safe_live_flag():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "$env:ATLAS_LIVE_TRADING = 'false'" in text


def test_orchestrator_requires_mt5_demo():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "$env:MT5_REQUIRE_DEMO = 'true'" in text


def test_required_groups_are_present():
    text = SCRIPT.read_text(encoding="utf-8")
    for name in ["repo_tests", "web_tests", "risk_safety", "api_smoke", "windows_integrity", "mt5_demo_runtime", "restart_reconnect"]:
        assert name in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_full_test_orchestrator_contract.py -q`
Expected: FAIL because script is absent.

- [ ] **Step 3: Create minimal safe PowerShell skeleton**

Create parameters, safe environment setup, group collection, non-zero exit on FAIL, and report-helper invocation. Do not add live execution code.

- [ ] **Step 4: Run contract tests**

Run: `python -m pytest tests/test_full_test_orchestrator_contract.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_full_test_orchestrator_contract.py scripts/run_full_atlas_test.ps1
git commit -m "test: scaffold ATLAS full test orchestrator"
```

### Task 3: Repository, Web, Risk, and Windows Groups

**Files:**
- Modify: `scripts/run_full_atlas_test.ps1`
- Test: `tests/test_full_test_orchestrator_contract.py`

**Interfaces:**
- Consumes: report helper from Task 1.
- Produces group result objects with `name`, `status`, `required`, `duration_seconds`, and optional `reason`.

- [ ] **Step 1: Add failing contract assertions**

Assert the script invokes:
- `python -m pytest -q`
- Node syntax/demo/auth tests
- `python scripts/build_website.py`
- focused risk/journal tests
- PowerShell parse of `scripts/deploy_google_cloud.ps1`

- [ ] **Step 2: Run contract tests and confirm failure**

Run: `python -m pytest tests/test_full_test_orchestrator_contract.py -q`
Expected: FAIL on missing command assertions.

- [ ] **Step 3: Implement groups**

Add a reusable `Invoke-AtlasGroup` helper that captures exit code, duration, and concise errors. Keep verbose subprocess output redirected to per-group log files under `artifacts/logs/`.

- [ ] **Step 4: Run contract tests and full Python suite**

Run: `python -m pytest tests/test_full_test_orchestrator_contract.py tests/test_atlas_test_report.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/run_full_atlas_test.ps1 tests/test_full_test_orchestrator_contract.py
git commit -m "test: orchestrate ATLAS repository and safety checks"
```

### Task 4: API and Docker Smoke Group

**Files:**
- Modify: `scripts/run_full_atlas_test.ps1`
- Test: `tests/test_full_test_orchestrator_contract.py`

**Interfaces:**
- `api_smoke` must verify `/health` == 200 and safe execution endpoint remains blocked in the test configuration.

- [ ] **Step 1: Add failing contract checks**

Require the script to probe `/health` and `/mt5/test-order`, and require expected status `403` for the execution endpoint under test-safe mode.

- [ ] **Step 2: Confirm failure**

Run: `python -m pytest tests/test_full_test_orchestrator_contract.py -q`
Expected: FAIL until probes exist.

- [ ] **Step 3: Implement API/Docker smoke**

When Docker is available and `-SkipDocker` is false, build the image, run it on an ephemeral localhost port, wait for health, assert `200`, assert protected execution path returns `403`, then clean up the container in `finally`.

- [ ] **Step 4: Run contract tests**

Run: `python -m pytest tests/test_full_test_orchestrator_contract.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/run_full_atlas_test.ps1 tests/test_full_test_orchestrator_contract.py
git commit -m "test: add ATLAS API and container smoke validation"
```

### Task 5: MT5 Demo Runtime Group

**Files:**
- Modify: `scripts/run_full_atlas_test.ps1`
- Reuse: existing `verify_mt5.py`, `run_atlas_mt5.py`, and current demo-status/monitor interfaces after confirming exact command signatures.
- Test: `tests/test_full_test_orchestrator_contract.py`

**Interfaces:**
- `mt5_demo_runtime` returns PASS only when a DEMO account, fresh quote feed, and one safe demo/paper ATLAS cycle are confirmed.
- Returns NOT_RUN with reason when the Windows host prerequisites are absent.
- Returns FAIL for LIVE account mode or stale/broken demo data.

- [ ] **Step 1: Inspect exact existing MT5 entry points**

Read `verify_mt5.py`, `run_atlas_mt5.py`, and `app/monitor/atlas_mt5.py`; record existing flags and outputs. Do not alter live-execution behavior.

- [ ] **Step 2: Add failing contract tests based on real entry points**

Require explicit demo-mode verification and quote-freshness check. Require a safe one-cycle command using the repository's existing demo/paper interface.

- [ ] **Step 3: Implement conditional MT5 stage**

Detect Windows, Python `MetaTrader5`, terminal/runtime availability, and required demo configuration. Run the verified existing demo checks. Refuse to proceed when account mode is not DEMO.

- [ ] **Step 4: Run contract tests**

Run: `python -m pytest tests/test_full_test_orchestrator_contract.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/run_full_atlas_test.ps1 tests/test_full_test_orchestrator_contract.py
git commit -m "test: add conditional MT5 demo runtime validation"
```

### Task 6: Restart/Reconnect and Idempotency Validation

**Files:**
- Modify: `scripts/run_full_atlas_test.ps1`
- Potentially add focused test file only if existing runtime interfaces expose restart/reconnect deterministically.

**Interfaces:**
- `restart_reconnect` must PASS only when duplicate protection can be proven safely; otherwise PARTIAL with a concrete missing prerequisite.

- [ ] **Step 1: Inspect current reconnect/idempotency interfaces**

Search existing tests and monitor/ledger code for restart, duplicate, reconciliation, and idempotency behavior.

- [ ] **Step 2: Add the smallest deterministic test available**

If a reusable interface exists, write a failing focused test that replays the same candidate/session identity across restart and expects a single ledger entry. If no safe deterministic interface exists, encode a contract that reports PARTIAL rather than PASS.

- [ ] **Step 3: Implement orchestrator stage**

Run the focused idempotency test or mark PARTIAL with the missing contract named explicitly.

- [ ] **Step 4: Run affected tests**

Run the focused restart/reconnect test plus the orchestrator contract tests.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/run_full_atlas_test.ps1 tests/
git commit -m "test: validate ATLAS restart and duplicate protection"
```

### Task 7: Documentation and CI Contract

**Files:**
- Create: `docs/ATLAS_FULL_TEST.md`
- Modify: `.github/workflows/tests.yml`

**Interfaces:**
- CI executes report/contract tests on every push/PR without requiring MT5 credentials.

- [ ] **Step 1: Add CI-safe tests locally**

Add `python -m pytest tests/test_atlas_test_report.py tests/test_full_test_orchestrator_contract.py -q` to the existing workflow after dependency installation.

- [ ] **Step 2: Document one-command usage**

Document:
```powershell
.\scripts\run_full_atlas_test.ps1
```
And report paths:
`artifacts/ATLAS_TEST_REPORT.json` and `artifacts/ATLAS_TEST_REPORT.md`.

- [ ] **Step 3: Verify workflow syntax and full suite**

Run:
`python -m pytest -q`
Expected: all tests pass.

- [ ] **Step 4: Run the orchestrator on an available Windows demo host**

Expected outcomes:
- PASS when all required checks plus MT5 demo runtime pass.
- PARTIAL when the desktop/demo environment is unavailable but repository checks pass.
- FAIL on any safety, test, API, or live-account violation.

- [ ] **Step 5: Commit**

```bash
git add docs/ATLAS_FULL_TEST.md .github/workflows/tests.yml
git commit -m "ci: add ATLAS full test orchestrator contract"
```

### Task 8: Final Verification

**Files:** No new files expected.

- [ ] **Step 1: Run full Python suite**

Run: `python -m pytest -q`
Expected: PASS with zero failures.

- [ ] **Step 2: Run web tests**

Run the same Node and website build commands used by CI.
Expected: PASS.

- [ ] **Step 3: Run orchestrator**

Run: `.\scripts\run_full_atlas_test.ps1`
Expected: PASS or PARTIAL only if MT5 prerequisites are unavailable; never false PASS.

- [ ] **Step 4: Inspect generated reports**

Confirm no secret values are present and that statuses match the actual executed groups.

- [ ] **Step 5: Open PR**

Create a PR from `codex/atlas-full-test-orchestrator` into `main` with CI evidence and the generated result summary, without committing secret-bearing runtime artifacts.
