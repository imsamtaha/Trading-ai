# ATLAS Engine Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate missing ATLAS engine capabilities into the existing deterministic demo/paper pipeline without duplicating working engines.

**Architecture:** Keep the current Python module layout and orchestrator as the canonical composition path. Extend intelligence with event context, add focused portfolio aggregation, and connect performance feedback while preserving execution and risk gates.

**Tech Stack:** Python, FastAPI, pytest, existing ATLAS intelligence/risk/execution modules.

**Spec:** `docs/superpowers/specs/2026-09-16-atlas-engine-integration-design.md`

## Global Constraints
- No monorepo migration for this milestone.
- No Redis/Prisma requirement.
- No broker order path may be added or bypass the existing gates.
- Keep live execution disabled; demo/paper validation only.
- Preserve existing APIs/dashboard behavior.
- TDD for behavior changes.

---

### Task 1: Engine composition contract

**Files:**
- Create: `app/intelligence/engine_hub.py`
- Create: `tests/test_atlas_engine_hub.py`

**Interfaces:**
- Produces: `EngineSnapshot` and `AtlasEngineHub.build_snapshot(...)`.
- Consumes existing technical, structure, regime/scoring, event context and optional account/position data as dictionaries.

- [ ] Write failing tests for deterministic engine snapshot composition and missing optional context.
- [ ] Run targeted tests and verify RED.
- [ ] Implement the minimal typed composition layer with no execution methods.
- [ ] Run targeted tests and verify GREEN.
- [ ] Refactor without changing behavior.

### Task 2: Event/news intelligence integration

**Files:**
- Modify: `app/intelligence/engine_hub.py`
- Modify: existing event/context adapter only if required by tests.
- Modify: `tests/test_atlas_engine_hub.py`

**Interfaces:**
- Consumes existing event/news outputs.
- Produces bounded event-risk/context fields for decision/scoring inputs.

- [ ] Add failing tests proving event context is represented but cannot authorize execution.
- [ ] Verify RED.
- [ ] Add minimal event normalization/composition.
- [ ] Verify GREEN plus existing event/scoring tests.

### Task 3: Portfolio exposure engine

**Files:**
- Create: `app/portfolio/__init__.py`
- Create: `app/portfolio/engine.py`
- Create: `tests/test_atlas_portfolio_engine.py`

**Interfaces:**
- Produces: `summarize_exposure(positions, equity)` returning deterministic exposure/count/concentration metadata.
- Does not place, modify, or close orders.

- [ ] Write failing exposure aggregation tests.
- [ ] Verify RED.
- [ ] Implement deterministic portfolio aggregation.
- [ ] Verify GREEN.

### Task 4: Performance feedback engine

**Files:**
- Modify: `app/performance/metrics.py` only if compatible; otherwise create `app/performance/feedback.py`.
- Create: `tests/test_atlas_performance_feedback.py`.

**Interfaces:**
- Produces descriptive demo/paper outcome summaries from closed trades.
- Must not auto-modify risk, thresholds, or execution settings.

- [ ] Write failing tests for closed-trade feedback and empty history.
- [ ] Verify RED.
- [ ] Implement minimal descriptive feedback.
- [ ] Verify GREEN.

### Task 5: Pipeline integration and regression safety

**Files:**
- Modify: `app/orchestrator.py` only where engine metadata can be attached without altering gate ordering.
- Modify/Create: integration tests under `tests/`.

**Interfaces:**
- Engine snapshot becomes observable decision-cycle metadata.
- Existing gate order remains SEAL/execution validation -> risk -> paper/live-disabled result.

- [ ] Write failing integration test proving the engine snapshot travels through a decision cycle.
- [ ] Write failing test proving no engine can bypass risk/execution gates.
- [ ] Verify RED.
- [ ] Wire the hub minimally into the orchestrator.
- [ ] Verify targeted GREEN.
- [ ] Run the full pytest suite and repository validation commands.
- [ ] Review diff for accidental live-execution enablement or API breakage.
