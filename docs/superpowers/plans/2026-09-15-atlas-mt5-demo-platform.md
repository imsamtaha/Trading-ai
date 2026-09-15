# ATLAS MT5 Demo Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fail-closed demo-only integration between ATLAS, its risk controls, and the existing MT5 adapter while adding the diversified asset universe.

**Architecture:** Add a canonical asset registry and broker-symbol resolver in front of the existing `MT5Broker`. Extend the execution gate so demo execution requires explicit policy, mapped assets, acceptable risk/spread, and duplicate-order protection; expose normalized broker state to the dashboard.

**Tech Stack:** Python 3, pytest, MetaTrader5 adapter, existing ATLAS execution/risk modules.

**Spec:** `docs/superpowers/specs/2026-09-15-atlas-mt5-demo-platform-design.md`

## Global Constraints
- Demo only.
- `ATLAS_LIVE_TRADING=false` remains the default and must not be changed by this plan.
- `MT5_REQUIRE_DEMO=true` is required for connected demo validation.
- Unknown symbols and missing market data fail closed.
- No broker credentials are exposed to dashboard payloads or logs.
- TDD: failing test before each production behavior change.

---

### Task 1: Canonical Asset Registry

**Files:**
- Create: `app/markets/assets.py`
- Create: `app/markets/__init__.py`
- Test: `tests/test_asset_registry.py`

**Interfaces:**
- Produces: `AssetSpec`, `CORE_ASSETS`, `get_asset(symbol: str)`, `assets_by_class(asset_class: str)`.

- [ ] Write tests asserting the registry contains Metals, Forex, Crypto, Indices, Energy and Stocks and the approved core symbols.
- [ ] Run `pytest tests/test_asset_registry.py -v` and verify RED because `app.markets.assets` does not exist.
- [ ] Implement immutable asset definitions with separate `analysis_enabled` and `demo_execution_enabled` flags; default demo execution to false.
- [ ] Run the test and verify GREEN.
- [ ] Commit `feat: add canonical ATLAS asset registry`.

### Task 2: MT5 Broker Symbol Resolver

**Files:**
- Create: `app/execution/symbols.py`
- Test: `tests/test_mt5_symbol_resolver.py`

**Interfaces:**
- Consumes: `CORE_ASSETS` and normalized dictionaries returned by `MT5Broker.symbols()`.
- Produces: `resolve_broker_symbol(canonical_symbol: str, broker_symbols: list[dict]) -> dict` with `canonical_symbol`, `broker_symbol`, `mapped`, and `reason`.

- [ ] Write tests for exact mapping, conservative normalized alias mapping, and an unknown symbol that returns `mapped=False`.
- [ ] Run the focused tests and verify RED.
- [ ] Implement deterministic resolution; never choose among ambiguous candidates.
- [ ] Run focused tests and verify GREEN.
- [ ] Commit `feat: add fail-closed MT5 symbol resolver`.

### Task 3: Demo Execution Risk Gate

**Files:**
- Modify: `app/execution/atlas.py`
- Reuse: `app/risk/manager.py`
- Test: `tests/test_atlas_demo_execution_gate.py`

**Interfaces:**
- Produces: a gate result that distinguishes `DEMO_EXECUTION_DISABLED`, `ASSET_NOT_ENABLED`, `SYMBOL_UNMAPPED`, `SPREAD_BLOCKED`, `RISK_REJECTED`, `DUPLICATE_ORDER`, and `APPROVED`.

- [ ] Write failing tests proving demo execution is disabled by default, unmapped assets fail closed, high spread fails closed, invalid risk/reward fails closed, and a valid demo intent can pass only with explicit demo policy.
- [ ] Run focused tests and verify RED.
- [ ] Extend policy and gate logic without enabling live trading.
- [ ] Run focused tests and verify GREEN.
- [ ] Commit `feat: add ATLAS demo execution risk gate`.

### Task 4: Duplicate Order Guard

**Files:**
- Create: `app/execution/idempotency.py`
- Test: `tests/test_execution_idempotency.py`

**Interfaces:**
- Produces: `ExecutionIntentGuard.accept(intent_id: str) -> bool` with bounded in-memory retention for the demo worker process.

- [ ] Write a failing test showing the first intent is accepted and the same intent is rejected on replay.
- [ ] Run focused test and verify RED.
- [ ] Implement the minimal bounded guard.
- [ ] Run focused test and verify GREEN.
- [ ] Commit `feat: prevent duplicate ATLAS demo execution intents`.

### Task 5: Dashboard Broker Snapshot

**Files:**
- Modify the existing dashboard MT5 state path after inspecting `app/dashboard/api.py` and `app/execution/mt5_state.py`.
- Test: extend `tests/test_atlas_mt5_readonly_dashboard.py`.

**Interfaces:**
- Produces a credential-free snapshot containing connection state, demo/live state, account summary, normalized positions and asset mapping status.

- [ ] Add failing assertions for the normalized snapshot and absence of password/credential fields.
- [ ] Run focused test and verify RED.
- [ ] Implement the minimal snapshot extension using existing dashboard conventions.
- [ ] Run focused test and verify GREEN.
- [ ] Commit `feat: expose ATLAS MT5 demo portfolio snapshot`.

### Task 6: Verification

**Files:** No production changes unless a failing test reveals a regression.

- [ ] Run all focused new tests.
- [ ] Run `pytest -q` for the complete suite.
- [ ] Confirm `.env.example` and `.env.mt5.example` keep live execution disabled by default.
- [ ] Inspect the branch diff for credentials, accidental live flags, and unrelated changes.
- [ ] Open a PR only after the suite is green; report any CI or environment limitation explicitly.
