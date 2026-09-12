# ATLAS Trader View, Filters, and Drawdown Alerts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add asset/timeframe performance filters, paper drawdown alerts, and a public-safe trader view to ATLAS without enabling live or broker execution.

**Architecture:** Extend the existing read-only demo analytics in `app/dashboard/demo_panel.py`, keeping aggregate metrics backward compatible while adding filtered metrics and alert derivation. Reuse the same data for a reduced `/dashboard/trader-view` response and browser UI controls, while preserving all existing paper-demo safety boundaries.

**Tech Stack:** Python 3.13, FastAPI, pytest, vanilla JavaScript/CSS, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-12-trader-view-alerts-design.md`

## Global Constraints

- `automatic_live_activation` remains `false`.
- No MT5 order endpoint is called or exposed.
- P/L remains `risk_normalized_pnl`, never broker-real P/L.
- Trader view must not expose account credentials, login, server, balance/equity, provider errors, or raw readiness internals.
- Filters are case-insensitive; missing or `ALL` means no restriction.
- Drawdown alert thresholds: NORMAL <20%, WATCH 20%-<35%, HIGH >=35%.

---

### Task 1: Filtered performance analytics

**Files:**
- Modify: `tests/test_demo_operations.py`
- Modify: `app/dashboard/demo_panel.py`

**Interfaces:**
- Consumes: closed paper trades from `MT5PaperLedger.closed_trades()`.
- Produces: `_performance_metrics(closed_trades, symbol=None, timeframe=None)` and `performance.filtered`, `performance.selection`, `performance.available_assets`, `performance.available_timeframes`.

- [ ] **Step 1: Write failing filter tests**

Add tests that seed EURUSD M5, EURUSD M15, and XAUUSD M5 closed trades and assert the endpoint returns correct filtered totals/win rates for `?asset=EURUSD&timeframe=M5`, correct available values, and zero metrics for an unknown asset.

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m pytest tests/test_demo_operations.py -q`
Expected: new assertions fail because filtered performance keys/query handling do not exist.

- [ ] **Step 3: Implement minimal filtering**

Normalize `asset` and `timeframe`, filter cloned trade dictionaries case-insensitively, keep existing aggregate fields unchanged, and return the filtered metric block plus selections and available lists.

- [ ] **Step 4: Run targeted tests**

Run: `python -m pytest tests/test_demo_operations.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

Commit message: `feat: add demo performance filters`

### Task 2: Drawdown monitoring alerts

**Files:**
- Modify: `tests/test_demo_operations.py`
- Modify: `app/dashboard/demo_panel.py`

**Interfaces:**
- Consumes: `readiness.max_drawdown_percent_of_total_risk`.
- Produces: `_drawdown_alert(drawdown_percent)` and top-level `alerts` in demo status.

- [ ] **Step 1: Write failing threshold tests**

Test exact mappings for 10 -> NORMAL, 20 -> WATCH, 34.99 -> WATCH, 35 -> HIGH, and assert `live_activation_blocked is True`.

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m pytest tests/test_demo_operations.py -q`
Expected: FAIL because `alerts` does not exist.

- [ ] **Step 3: Implement alert derivation**

Implement a pure helper with the documented thresholds and concise messages. Add its output to `/dashboard/demo-status` without changing readiness or execution flags.

- [ ] **Step 4: Run targeted tests**

Run: `python -m pytest tests/test_demo_operations.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

Commit message: `feat: add paper drawdown alerts`

### Task 3: Public-safe trader view API

**Files:**
- Modify: `tests/test_demo_operations.py`
- Modify: `app/dashboard/demo_panel.py`

**Interfaces:**
- Consumes: same ledger/session data as demo status.
- Produces: `GET /dashboard/trader-view` reduced public-safe JSON.

- [ ] **Step 1: Write failing trader-view tests**

Assert the response includes `paper_demo=true`, `broker_orders=false`, counts, performance, and alert summary; assert serialized output omits `login`, `server`, `balance`, `equity`, `provider`, and raw `readiness`.

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m pytest tests/test_demo_operations.py -q`
Expected: 404 for `/dashboard/trader-view`.

- [ ] **Step 3: Implement reduced endpoint**

Create a read-only endpoint that accepts the same optional filters and returns only approved fields from the spec. Do not reuse raw session events or account telemetry.

- [ ] **Step 4: Run targeted tests**

Run: `python -m pytest tests/test_demo_operations.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

Commit message: `feat: add public safe trader view`

### Task 4: Performance Center controls and alert UI

**Files:**
- Modify: `tests/test_demo_operations.py`
- Modify: `app/dashboard/demo_panel.py`

**Interfaces:**
- Consumes: `/dashboard/demo-status?asset=<>&timeframe=<>`.
- Produces: Asset/Timeframe select controls and Drawdown Alert badge/message in the existing demo panel.

- [ ] **Step 1: Write failing UI assertions**

Assert `/ui/demo-panel.js` contains `demo-asset-filter`, `demo-timeframe-filter`, `Drawdown Alert`, and query parameter construction for `asset` and `timeframe`.

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m pytest tests/test_demo_operations.py -q`
Expected: FAIL because controls are absent.

- [ ] **Step 3: Implement controls**

Populate options from `available_assets`/`available_timeframes`, preserve selection across refreshes, fetch filtered data on change, render alert level/message, and keep all execution controls absent.

- [ ] **Step 4: Run targeted tests**

Run: `python -m pytest tests/test_demo_operations.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

Commit message: `feat: add performance filters and alert UI`

### Task 5: Full regression verification

**Files:**
- No production changes unless a regression is found.

**Interfaces:**
- Produces: verified branch ready for PR/merge.

- [ ] **Step 1: Run full Python suite**

Run: `python -m pytest -q`
Expected: 0 failures.

- [ ] **Step 2: Run public website checks**

Run: `node --check web/assets/site.js && node --test tests/test_demo_model.cjs && node --test tests/test_google_auth.mjs && node --check web/assets/google-auth.js && python scripts/build_website.py`
Expected: all commands exit 0.

- [ ] **Step 3: Open PR and confirm GitHub Actions**

Open a PR from `atlas/trader-view-alerts` to `main`; require the `tests` workflow to complete successfully before merge.

- [ ] **Step 4: Merge only after fresh green CI**

Use the PR head SHA as the expected merge SHA and verify the push workflow on `main` also succeeds.
