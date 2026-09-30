# Execution Guard Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an ATLAS Execution Guard Agent that converts advisory council decisions into safe Demo auto-execution or Live trade drafts requiring one explicit confirmation for that exact draft before broker submission.

**Architecture:** Introduce a focused `app/execution_guard` module between council output and the existing MT5 service. The guard owns decision validation, freshness, risk/account checks, idempotency, draft lifecycle, and audit events, while existing `MT5Broker.market_order()` remains the final broker adapter. Demo orders may auto-submit only when demo execution is enabled; REAL accounts never bypass per-draft human confirmation.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, pytest, existing `MT5DemoService`, `MT5Broker`, Supabase repository layer, React/Next.js dashboard.

**Spec:** `docs/plans/2026-09-29-execution-guard-agent-spec.md`

## Global Constraints

- Council decisions accepted only for `BUY`, `SELL`, or `WAIT`.
- `WAIT`, stale, incomplete, or inconsistent decisions never reach broker execution.
- Existing broker-side SL/TP, volume, account-mode, account-login, and 1% stop-loss risk checks remain authoritative.
- Demo auto-execution requires a connected DEMO account and demo order execution enabled.
- REAL accounts create a `TradeDraft`; broker submission requires authenticated explicit confirmation of that exact unexpired draft.
- No blanket approval token, background autonomous live execution, or automatic retry after unknown broker outcome.
- Every decision outcome is user-scoped and auditable.
- Live broker execution remains disabled by environment during implementation and verification.

## Review Focus

- Expired or stale decisions must block before any broker call.
- Duplicate `decision_id` / `draft_id` must never cause a second submission.
- Account login or mode changes between evaluation and confirmation must block submission.
- Malformed NaN/Infinity or directionally invalid SL/TP must block safely.
- Unknown broker outcome must record `UNKNOWN` and require manual history inspection, never auto-retry.

---
### Task 1: Execution Guard domain models

**Files:**
- Create: `app/execution_guard/__init__.py`
- Create: `app/execution_guard/models.py`
- Test: `tests/test_execution_guard_models.py`

**Interfaces:**
- Produces: `CouncilDecision`, `GuardResult`, `TradeDraft`, `ExecutionEvent` Pydantic models.
- `CouncilDecision` fields: `decision_id`, `symbol`, `direction`, `confidence`, `rationale`, `timestamp`, `volume`, `stop_loss`, `take_profit`, `risk_context`.
- `TradeDraft` fields include `draft_id`, `user_id`, account fingerprint, council evidence, expiry, and status.

- [ ] **Step 1: Write failing validation tests** for WAIT/BUY/SELL parsing, finite numeric fields, required SL/TP for actionable decisions, and immutable identifiers.
- [ ] **Step 2: Run** `python -m pytest tests/test_execution_guard_models.py -q`; expect failures because the module does not exist.
- [ ] **Step 3: Implement the four models** with strict finite-number and enum validation; WAIT may omit trade parameters, BUY/SELL may not.
- [ ] **Step 4: Re-run the model tests** and require all pass.
- [ ] **Step 5: Commit** `feat(execution-guard): add decision and draft models`.

### Task 2: Guard evaluation service

**Files:**
- Create: `app/execution_guard/service.py`
- Test: `tests/test_execution_guard_service.py`

**Interfaces:**
- Consumes: `CouncilDecision`; existing MT5 session/dashboard data.
- Produces: `ExecutionGuardService.evaluate(user_id: str, decision: CouncilDecision) -> GuardResult | TradeDraft | dict`.
- Dependencies are injected: repository, MT5 service, execution broker factory, clock.
- [ ] **Step 1: Write failing service tests** proving WAIT, low confidence, stale timestamp, invalid SL/TP, changed account mode, and duplicate decision IDs are `BLOCKED` without broker calls.
- [ ] **Step 2: Add failing Demo test** proving a valid DEMO decision auto-submits only when demo execution is enabled, and records `EXECUTED`.
- [ ] **Step 3: Add failing REAL test** proving valid REAL input returns `WAITING_CONFIRMATION` plus a draft and makes zero broker order calls.
- [ ] **Step 4: Run** `python -m pytest tests/test_execution_guard_service.py -q`; verify RED for missing implementation.
- [ ] **Step 5: Implement minimal guard logic**: configurable confidence threshold, freshness window, account/session match, decision idempotency, draft generation, and broker handoff for DEMO only.
- [ ] **Step 6: Re-run tests** and require all pass.
- [ ] **Step 7: Commit** `feat(execution-guard): evaluate council decisions`.

### Task 3: Audit persistence and draft lifecycle

**Files:**
- Modify: `app/users/repository.py`
- Create: `supabase/migrations/20260929_execution_guard_events.sql`
- Test: `tests/test_execution_guard_audit.py`

**Interfaces:**
- Add repository methods: `add_execution_guard_event`, `list_execution_guard_events`, `save_trade_draft`, `get_trade_draft`, `mark_trade_draft`.
- Persistence is user-scoped; draft lookup must bind `draft_id` and `user_id`.

- [ ] **Step 1: Write failing memory-repository tests** for isolated events, duplicate draft protection, expiry/status updates, and cross-user lookup rejection.
- [ ] **Step 2: Run** `python -m pytest tests/test_execution_guard_audit.py -q`; verify RED.
- [ ] **Step 3: Implement Memory repository methods** with deep-copy semantics matching existing patterns.
- [ ] **Step 4: Add Supabase methods and migration** for `execution_guard_events` and `execution_guard_drafts`, including unique `(user_id, decision_id)` and draft primary key constraints.
- [ ] **Step 5: Re-run audit tests** and require all pass.
- [ ] **Step 6: Commit** `feat(execution-guard): persist drafts and audit events`.

### Task 4: Live draft confirmation boundary

**Files:**
- Modify: `app/execution_guard/service.py`
- Test: `tests/test_execution_guard_confirmation.py`

**Interfaces:**
- Produces: `confirm(user_id: str, draft_id: str) -> dict[str, Any]`.
- Confirmation must re-read the connected MT5 session and verify user, account fingerprint, mode `REAL`, expiry, and draft status before broker submission.
- [ ] **Step 1: Write failing confirmation tests** for wrong user, expired draft, already-consumed draft, changed login/mode, and valid exact-draft confirmation.
- [ ] **Step 2: Add unknown-outcome test** proving broker exceptions mark audit `UNKNOWN` and never auto-retry.
- [ ] **Step 3: Run** `python -m pytest tests/test_execution_guard_confirmation.py -q`; verify RED.
- [ ] **Step 4: Implement `confirm()`** by revalidating draft/session state, reserving idempotency before broker call, then delegating once to existing `MT5Broker.market_order()` through the execution factory.
- [ ] **Step 5: Re-run confirmation tests** and require all pass.
- [ ] **Step 6: Commit** `feat(execution-guard): confirm live trade drafts safely`.

### Task 5: Authenticated API routes and CSRF boundary

**Files:**
- Create: `app/execution_guard/routes.py`
- Modify: `app/main.py` or router registration module used by the app
- Test: `tests/test_execution_guard_routes.py`

**Interfaces:**
- `POST /api/execution-guard/evaluate`
- `GET /api/execution-guard/status`
- `GET /api/execution-guard/events`
- `POST /api/execution-guard/confirm/{draft_id}`

- [ ] **Step 1: Write failing route tests** for unauthenticated 401, cross-origin cookie POST 403, malformed payload 422, user isolation, and successful evaluate/confirm responses.
- [ ] **Step 2: Run** `python -m pytest tests/test_execution_guard_routes.py -q`; verify RED.
- [ ] **Step 3: Implement routes** using `require_user()` and the existing same-origin check pattern from `app/mt5_demo/routes.py`.
- [ ] **Step 4: Re-run route tests** and require all pass.
- [ ] **Step 5: Commit** `feat(api): expose execution guard agent routes`.

### Task 6: Dashboard feature flag and execution-agent sector

**Files:**
- Modify: `app/users/routes.py`
- Modify frontend dashboard state mapper/types in `web/lib/api/`
- Create or modify: `web/features/execution/execution-agent-panel.tsx`
- Modify: `web/features/dashboard/dashboard-screen.tsx`
- Test: backend dashboard feature test plus `web/tests/execution-agent-panel.test.tsx`

**Interfaces:**
- Dashboard payload adds `execution_guard` feature availability and current guard status.
- UI renders council decision/confidence, READY/BLOCKED/EXECUTED/WAITING CONFIRMATION, concise reason, draft summary, and audit timeline.
- Live confirmation control submits only the selected `draft_id`; no reusable approval state is stored client-side.

- [ ] **Step 1: Write failing backend/frontend tests** for feature availability, hidden state when unavailable, status rendering, and exact-draft confirmation payload.
- [ ] **Step 2: Run targeted backend and frontend tests**; verify RED.
- [ ] **Step 3: Extend dashboard API/mappers/types** with execution guard state.
- [ ] **Step 4: Implement `EXECUTION AGENT` sector** using the existing ATLAS 3D visual language without profit/guarantee wording.
- [ ] **Step 5: Re-run targeted tests** and require all pass.
- [ ] **Step 6: Commit** `feat(web): add execution agent sector`.

### Task 7: Full-system verification and safe rollout

**Files:**
- Modify only if verification exposes a defect.
- Verify runner/env files without enabling live execution.

- [ ] **Step 1: Run backend guard suite**: `python -m pytest tests/test_execution_guard_models.py tests/test_execution_guard_service.py tests/test_execution_guard_audit.py tests/test_execution_guard_confirmation.py tests/test_execution_guard_routes.py -q`.
- [ ] **Step 2: Run full backend suite**: `python -m pytest -q`; require zero failures.
- [ ] **Step 3: Run full frontend suite**: from `web`, `npx vitest run --maxWorkers=1`; require zero failures.
- [ ] **Step 4: Run frontend production build**: `npm run build`; require exit code 0.
- [ ] **Step 5: Verify environment remains safe**: `ATLAS_LIVE_TRADING=false`; no REAL broker execution flag enabled during rollout verification.
- [ ] **Step 6: Verify Demo path with fake/stub broker first**, then a DEMO MT5 account only if explicitly connected; confirm one decision creates one audit result.
- [ ] **Step 7: Verify REAL path never submits without exact draft confirmation** using fake broker tests only; do not send a real-money order during verification.
- [ ] **Step 8: Inspect `git diff --check`, `git status --short`, and commit history** for only intended files.
- [ ] **Step 9: Commit final integration** `feat(atlas): integrate execution guard agent` and push the feature branch.

## Self-Review

- Spec coverage: council validation, risk/account checks, Demo auto-execution, Live draft confirmation, idempotency, audit, API, UI, and rollout are mapped to Tasks 1-7.
- Type consistency: `CouncilDecision`, `TradeDraft`, and `ExecutionGuardService.evaluate/confirm` are defined once and consumed downstream.
- Review Focus items are explicitly covered by Tasks 2-5.
- No task enables autonomous REAL execution or removes exact-draft confirmation.
- Existing `MT5Broker.market_order()` remains the final broker risk boundary; the plan does not duplicate its broker logic.