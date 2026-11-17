# ATLAS Execution Modes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement owner-only paper mode plus isolated customer MT5 demo and real-account execution modes without using a global dry-run flag as authorization.

**Architecture:** Introduce an immutable per-request execution context and centralized mode/account authorization before dispatch to dedicated paper or MT5 execution adapters. Preserve existing risk gates and add account isolation, emergency-stop and audit requirements around customer execution.

**Tech Stack:** Python, FastAPI, MetaTrader5 Windows adapter, pytest/unittest, GitHub Actions, Cloudflare Tunnel.

**Spec:** `docs/superpowers/specs/2026-09-25-execution-modes-design.md`

## Global Constraints
- PAPER is owner-only and never sends broker orders.
- LIVE_DEMO accepts only the authenticated customer's MT5 demo account.
- LIVE_EXECUTION accepts only the authenticated customer's MT5 real account.
- Customer accounts are isolated by `user_id + account_id`.
- Risk Manager, execution gate, emergency stop and audit logging remain fail-closed.
- Validation/tests never send a real-money order.
- Do not alter unrelated DNS/mail records during deployment.

## Review Focus
- Forged `account_id` for another user must fail closed.
- Unknown/CONTEST MT5 trade mode must fail closed.
- Customer PAPER access must fail even if request parameters are forged.
- Emergency-stop state must block customer execution before broker dispatch.
- Missing/stale broker account metadata must block execution.

---

### Task 1: Execution context and mode authorization

**Files:**
- Create: `app/execution/context.py`
- Create: `tests/test_execution_context.py`

**Interfaces:**
- Produces: `ExecutionMode`, `ExecutionContext`, `ExecutionAuthorizationError`, `authorize_execution_context(context, broker_account)`.

- [ ] Write tests proving owner PAPER passes; customer PAPER fails; LIVE_DEMO requires DEMO; LIVE_EXECUTION requires REAL; CONTEST/unknown fail; mismatched account ownership fails.
- [ ] Run `python -m pytest tests/test_execution_context.py -q` and verify RED.
- [ ] Implement enum/dataclass and fail-closed authorization with MT5 mode constants 0=DEMO, 1=CONTEST, 2=REAL.
- [ ] Re-run focused tests and verify PASS.
- [ ] Commit `feat: add per-account execution context`.

### Task 2: Separate paper dispatch from MT5 dispatch

**Files:**
- Create: `app/execution/paper.py`
- Modify: `app/execution/atlas.py`
- Test: `tests/test_execution_dispatch.py`

**Interfaces:**
- Consumes: `ExecutionContext` from Task 1.
- Produces: mode-aware dispatch where PAPER never calls `MT5Broker.market_order`.

- [ ] Add failing tests using a broker spy to prove PAPER cannot invoke MT5 and customer modes cannot fall through to paper.
- [ ] Run focused tests and verify RED.
- [ ] Implement a dedicated paper adapter and explicit dispatcher; do not infer actor/mode from `MT5Config.dry_run`.
- [ ] Run focused tests and verify PASS.
- [ ] Commit `refactor: isolate paper and MT5 execution`.

### Task 3: Customer account isolation and emergency stop

**Files:**
- Create: `app/execution/accounts.py`
- Create: `app/execution/emergency_stop.py`
- Test: `tests/test_execution_isolation.py`

**Interfaces:**
- Produces: account ownership lookup scoped by `(user_id, account_id)` and `EmergencyStopStore.is_blocked(user_id, account_id)`.

- [ ] Add failing tests for cross-user account access, unknown account, stopped account and independent stop state between accounts.
- [ ] Run focused tests and verify RED.
- [ ] Implement fail-closed ownership resolution and account-scoped emergency stop.
- [ ] Run focused tests and verify PASS.
- [ ] Commit `feat: enforce customer account isolation`.

### Task 4: Audit every customer execution attempt

**Files:**
- Create: `app/execution/audit.py`
- Modify: execution dispatcher/service from Task 2.
- Test: `tests/test_execution_audit.py`

**Interfaces:**
- Produces: immutable audit events containing user/account/mode, decision, gate result, broker result category and timestamp; never credentials.

- [ ] Add failing tests for approved, blocked, broker-error and emergency-stop attempts; assert credentials are absent.
- [ ] Run focused tests and verify RED.
- [ ] Implement audit recording before/after dispatch with fail-safe error recording.
- [ ] Run focused tests and verify PASS.
- [ ] Commit `feat: audit customer execution attempts`.

### Task 5: API routing and authenticated mode exposure

**Files:**
- Modify: `app/main.py` (or the current FastAPI router containing MT5 routes).
- Modify/Create tests for API execution routes.

**Interfaces:**
- Consumes: authenticated user identity, owned account resolver, execution context, emergency stop and dispatcher.

- [ ] Add failing API tests: customer cannot request PAPER, cannot forge another account, DEMO/REAL mismatch returns 403, emergency stop returns 403, missing confirmation/authorization returns 403.
- [ ] Run focused API tests and verify RED.
- [ ] Replace global-mode authorization in customer routes with authenticated per-account context; retain owner-only private paper route.
- [ ] Run focused tests and verify PASS.
- [ ] Commit `feat: route execution by authenticated account`.

### Task 6: Dashboard mode separation

**Files:**
- Modify current dashboard templates/static assets discovered from repository search.
- Test current dashboard/API presentation tests.

**Interfaces:**
- Owner UI: PAPER only in owner workspace.
- Customer UI: LIVE_DEMO / LIVE_EXECUTION status for owned account only.

- [ ] Add presentation tests asserting Paper is absent from customer output and credentials are never rendered.
- [ ] Implement mode-specific status/actions using existing project UI conventions.
- [ ] Run dashboard tests.
- [ ] Commit `feat: separate owner and customer execution UI`.

### Task 7: Full regression and Windows MT5 validation

**Files:**
- Modify tests/scripts only if a reproducible compatibility defect is found.

- [ ] Run all focused execution tests.
- [ ] Run `python -m pytest -q`; require zero failures.
- [ ] On Windows with MT5 open, verify connection, account metadata/trade mode, fresh quote, positions read, disconnect/reconnect and emergency-stop behavior.
- [ ] Verify no validation step invokes a real-money `order_send`.
- [ ] Push branch and require GitHub Actions success before merge.

### Task 8: Production service and external domain verification

**Files:**
- Deployment configuration/scripts only where required by the existing repository.

- [ ] Start/restart ATLAS Windows production service and verify local `/health`.
- [ ] Confirm Cloudflare `ATLAS-Window` connector is Healthy.
- [ ] Route `justai-atlas.online` to the verified local ATLAS HTTP service; resolve only conflicting web-host records and preserve mail records.
- [ ] Verify externally: `https://justai-atlas.online/`, `/dashboard`, `/health` return the intended ATLAS application.
- [ ] Record final commit/PR, CI result, MT5 validation status, Cloudflare status and any remaining blocker. Do not claim Live until external HTTP verification succeeds.
