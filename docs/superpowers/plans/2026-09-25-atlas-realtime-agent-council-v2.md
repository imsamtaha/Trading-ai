# ATLAS Realtime Agent Council v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a customer-first realtime multi-agent ATLAS path for LIVE_DEMO with auditable decisions, customer isolation, confidence calibration, rescue monitoring, notifications, and no paper-trading terminology in customer-facing runtime.

**Architecture:** Add a new `app/customer` subsystem beside the frozen legacy path. Each cycle creates one immutable snapshot, runs specialist agents against that snapshot, resolves conflicts in a coordinator, calibrates confidence, applies deterministic capital/risk checks, routes to the correct execution adapter, then continues monitoring through a separate Rescue Agent. The first shipped execution target is LIVE_DEMO; production execution remains a separate adapter/interface and is not activated by this plan.

**Tech Stack:** Python, FastAPI, pytest, existing ATLAS MT5 connector/risk modules, existing project logging/audit patterns.

**Spec:** `docs/superpowers/specs/2026-09-25-atlas-realtime-agent-council-v2-design.md`

## Global Constraints

- Customer runtime must not expose `paper_only`, `PAPER_CANDIDATE`, paper routing, or paper execution terminology.
- All agents in one cycle must reference the same immutable `snapshot_id`.
- Missing/stale critical data must fail safe to non-entry behavior.
- No agent may hold broker credentials or call MT5 order placement directly.
- Capital Guardian and deterministic risk validation remain independent of confidence scoring.
- Rescue Agent must be independent from Trader Agent.
- Every customer-scoped record must carry `customer_id`, `account_id`, and `mode`.
- LIVE_DEMO is the first end-to-end execution target.
- Legacy code is frozen until v2 passes acceptance tests; deletion is a separate cleanup change.

## Review Focus

- Mixed snapshot timestamps or IDs must never be combined into one decision.
- A stale feed, MT5 disconnect, or broken critical safety component must block new demo execution.
- Cross-customer access must be rejected even when object IDs are valid.
- Duplicate decision/execution events must be idempotent and not create duplicate demo orders.
- Rescue decisions must not depend on the Trader Agent state and must still work after restart/reload from persisted position state.

---

### Task 1: Customer Contracts and Immutable Snapshot

**Files:**
- Create: `app/customer/__init__.py`
- Create: `app/customer/contracts.py`
- Create: `app/customer/realtime/snapshot.py`
- Test: `tests/customer/test_snapshot_contracts.py`

**Interfaces:**
- Consumes: normalized market/account/system inputs from existing adapters.
- Produces: `CustomerContext`, `MarketSnapshot`, `AgentVerdict`, `DecisionCandidate` dataclasses and `build_snapshot(...) -> MarketSnapshot`.

- [ ] **Step 1: Write failing tests** for required IDs/mode fields, immutable snapshot semantics, same-cycle identity, and stale timestamp detection.
- [ ] **Step 2: Run** `python -m pytest tests/customer/test_snapshot_contracts.py -q` and confirm failures.
- [ ] **Step 3: Implement minimal contracts and snapshot builder** with explicit enums for mode/status/signal/decision.
- [ ] **Step 4: Re-run targeted tests** and confirm PASS.
- [ ] **Step 5: Commit** `feat: add customer snapshot contracts`.

### Task 2: Specialist Agents and Shared Base Contract

**Files:**
- Create: `app/customer/agents/base.py`
- Create: `app/customer/agents/technical.py`
- Create: `app/customer/agents/news.py`
- Create: `app/customer/agents/sentiment.py`
- Create: `app/customer/agents/regime.py`
- Create: `app/customer/agents/financial_monitor.py`
- Create: `app/customer/agents/system_watchdog.py`
- Test: `tests/customer/test_specialist_agents.py`

**Interfaces:**
- Consumes: `MarketSnapshot`.
- Produces: `evaluate(snapshot: MarketSnapshot) -> AgentVerdict` per specialist.

- [ ] **Step 1: Write failing tests** proving every verdict contains agent name, timestamp, snapshot ID, status, confidence, evidence, blockers, data quality, latency.
- [ ] **Step 2: Add tests** for `UNAVAILABLE` on missing news/sentiment data and `DEGRADED`/blocker behavior for stale system/market data.
- [ ] **Step 3: Run targeted tests** and confirm failures.
- [ ] **Step 4: Implement specialists** using existing deterministic analysis utilities where available; never invent missing external data.
- [ ] **Step 5: Re-run tests** and confirm PASS.
- [ ] **Step 6: Commit** `feat: add realtime specialist agents`.

### Task 3: Coordinator, Conflict Resolution, Confidence and Capital Guardian

**Files:**
- Create: `app/customer/agents/coordinator.py`
- Create: `app/customer/agents/confidence.py`
- Create: `app/customer/agents/capital_guardian.py`
- Create: `app/customer/realtime/conflict.py`
- Create: `app/customer/realtime/weighting.py`
- Test: `tests/customer/test_coordination.py`

**Interfaces:**
- Consumes: one `MarketSnapshot` plus `list[AgentVerdict]`.
- Produces: `coordinate(snapshot, verdicts) -> DecisionCandidate`, `calibrate_confidence(...) -> float`, `evaluate_capital(...) -> CapitalDecision`.

- [ ] **Step 1: Write failing tests** for weighted conflict handling, stale-agent exclusion, event-risk conflict, evidence concentration penalty, and no simple-majority shortcut.
- [ ] **Step 2: Write tests** enforcing high confidence only with multiple independent fresh factors and no unresolved critical blocker.
- [ ] **Step 3: Write tests** proving Capital Guardian can veto independently of directional consensus/confidence.
- [ ] **Step 4: Run tests** and confirm failures.
- [ ] **Step 5: Implement minimal coordinator/conflict/confidence/capital logic**.
- [ ] **Step 6: Re-run tests** and confirm PASS.
- [ ] **Step 7: Commit** `feat: add council coordination and capital guardian`.

### Task 4: Trader Agent, Deterministic Risk Bridge, and LIVE_DEMO Router

**Files:**
- Create: `app/customer/agents/trader.py`
- Create: `app/customer/execution/mode_router.py`
- Create: `app/customer/execution/demo_adapter.py`
- Create: `app/customer/execution/production_adapter.py`
- Modify: `app/risk/manager.py` only if required to expose a reusable customer-facing call without changing risk policy.
- Test: `tests/customer/test_execution_routing.py`

**Interfaces:**
- Consumes: approved `DecisionCandidate`, account state, deterministic risk result.
- Produces: `TradeIntent`, `ExecutionResult`, `ModeRouter.execute_demo(...)`.

- [ ] **Step 1: Write failing tests** proving Trader Agent cannot place orders directly and only produces a structured intent.
- [ ] **Step 2: Add tests** for risk rejection, invalid SL/TP, duplicate trace/idempotency, stale connector state, and LIVE_DEMO routing.
- [ ] **Step 3: Add test** proving client payload cannot switch mode into production execution.
- [ ] **Step 4: Run tests** and confirm failures.
- [ ] **Step 5: Implement demo adapter using verified existing MT5 connector interfaces**; keep production adapter isolated and non-active.
- [ ] **Step 6: Re-run tests** and confirm PASS.
- [ ] **Step 7: Commit** `feat: add live demo execution router`.

### Task 5: Position Monitor, Rescue Agent, Notifications, and Audit Trace

**Files:**
- Create: `app/customer/agents/rescue.py`
- Create: `app/customer/monitoring/position_monitor.py`
- Create: `app/customer/monitoring/notifications.py`
- Create: `app/customer/audit.py`
- Test: `tests/customer/test_rescue_monitoring.py`

**Interfaces:**
- Consumes: open position state, latest snapshot/system health, trace ID.
- Produces: `RescueDecision` with `HOLD|REDUCE|EXIT|PROTECT|HALT`, persisted audit events, notification payloads.

- [ ] **Step 1: Write failing tests** for volatility spike, spread anomaly, reversal, rapid drawdown, stale feed, and connector failure.
- [ ] **Step 2: Add test** proving Rescue Agent works independently of Trader Agent and from persisted position state after reload.
- [ ] **Step 3: Add notification/audit tests** linking each intervention and execution result to the matching customer trace.
- [ ] **Step 4: Run tests** and confirm failures.
- [ ] **Step 5: Implement rescue/monitoring/notification/audit modules**.
- [ ] **Step 6: Re-run tests** and confirm PASS.
- [ ] **Step 7: Commit** `feat: add rescue monitoring and notifications`.

### Task 6: Shadow, Replay, Calibration, and Agent Health

**Files:**
- Create: `app/customer/validation/shadow.py`
- Create: `app/customer/validation/replay.py`
- Create: `app/customer/validation/calibration.py`
- Create: `app/customer/validation/health.py`
- Test: `tests/customer/test_validation_layer.py`

**Interfaces:**
- Consumes: stored snapshots, agent verdicts, decisions, outcomes.
- Produces: deterministic replay reports, shadow outcomes, confidence-bucket metrics, agent-health metrics.

- [ ] **Step 1: Write failing tests** for deterministic replay, shadow non-execution, confidence buckets, and health degradation from stale/error/latency inputs.
- [ ] **Step 2: Add scenario tests** for high-impact news, gap/spread spike, MT5 disconnect, duplicate signal, conflicting agents, and rapid drawdown.
- [ ] **Step 3: Run tests** and confirm failures.
- [ ] **Step 4: Implement validation layer** with persisted metrics using existing project persistence patterns.
- [ ] **Step 5: Re-run tests** and confirm PASS.
- [ ] **Step 6: Commit** `feat: add agent validation and replay`.

### Task 7: Customer API v2 and Isolation

**Files:**
- Create: `app/customer/api/router.py`
- Create: `app/customer/service.py`
- Modify: `app/main.py` to mount the customer v2 router.
- Test: `tests/customer/test_customer_api.py`
- Test: `tests/customer/test_customer_isolation.py`

**Interfaces:**
- Consumes: customer/account identity from existing auth boundary plus customer services from Tasks 1-6.
- Produces: `/api/v2/customer/account`, `/positions`, `/decisions/latest`, `/agents/status`, `/alerts`, `/rescue/status`, `/cycle/demo`, internal replay/audit routes.

- [ ] **Step 1: Write failing endpoint tests** for response shapes and trace IDs.
- [ ] **Step 2: Write isolation tests** proving one customer cannot read another customer's positions, snapshots, alerts, decisions, or audit traces.
- [ ] **Step 3: Add tests** proving customer API contains no paper terminology.
- [ ] **Step 4: Run tests** and confirm failures.
- [ ] **Step 5: Implement router/service and mount into FastAPI**.
- [ ] **Step 6: Re-run tests** and confirm PASS.
- [ ] **Step 7: Commit** `feat: add customer realtime api v2`.

### Task 8: End-to-End LIVE_DEMO Validation and Legacy Freeze

**Files:**
- Create: `tests/customer/test_live_demo_e2e.py`
- Modify: legacy customer-facing routes/imports only as needed to remove paper-oriented customer exposure; do not delete legacy modules yet.
- Update: `README.md` and/or customer runtime docs with v2 entrypoints.

**Interfaces:**
- Consumes: full Tasks 1-7 stack and existing MT5 demo connector.
- Produces: one auditable end-to-end LIVE_DEMO cycle and documented v2 runtime path.

- [ ] **Step 1: Write E2E test** from customer context -> snapshot -> agents -> coordination -> capital/risk -> demo adapter -> position monitoring -> audit/notification.
- [ ] **Step 2: Add failure-path E2E tests** for stale data, MT5 disconnect, duplicate execution, and cross-customer access.
- [ ] **Step 3: Run customer suite** `python -m pytest tests/customer -q` and fix only v2/customer regressions.
- [ ] **Step 4: Run full suite** `python -m pytest -q` and confirm existing verified core tests remain passing.
- [ ] **Step 5: Search customer runtime/UI/API code for paper terminology** and remove remaining customer-facing references without deleting legacy implementation.
- [ ] **Step 6: Run final verification** including `/health` and customer v2 API smoke checks.
- [ ] **Step 7: Commit** `feat: finalize atlas realtime customer v2`.

## Completion Gate

Implementation is complete only when:
- `python -m pytest tests/customer -q` passes.
- `python -m pytest -q` passes or any pre-existing unrelated failure is explicitly identified with evidence.
- LIVE_DEMO E2E passes through the MT5 demo adapter.
- No customer-facing runtime/API contains paper-trading terminology.
- Isolation, idempotency, stale-data, watchdog, rescue, audit, and replay tests pass.
- A decision trace can be reconstructed from snapshot through agent verdicts, coordinator, confidence, capital/risk, demo execution, monitoring, rescue, notification, and audit.
