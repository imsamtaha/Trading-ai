# ATLAS Realtime Agent Council v2.1

Revision notes vs v2: live execution is now a fully specified subsystem (eligibility, order lifecycle, safety controls, reconciliation, rollout gates); simulation-era concepts are removed from the customer runtime; authority boundaries between agents are explicit; LLM/deterministic separation is enforced; decision TTL, idempotency, kill switches and failure semantics are defined.

## 1. Purpose

Build the customer-first ATLAS decision subsystem: a real-time multi-agent intelligence path that continuously observes market, news, sentiment, account, execution and system state; forms a current decision from the latest evidence; monitors positions after entry; notifies the customer; and activates a rescue path when conditions deteriorate.

Two execution modes share one intelligence path:

- `LIVE_DEMO`: live market data, demo-account execution.
- `LIVE_EXECUTION`: real-money execution through an isolated production adapter.

The mode changes only the execution adapter and the safety envelope. It never changes the decision logic.

## 2. Scope

Covers the new customer runtime only. Legacy orchestration stays frozen for reference until v2 passes acceptance. Verified reusable components (MT5 connectors, deterministic risk math, auth, market-data adapters, audit utilities) may be retained.

**Removed from the customer runtime:** all simulation-only routing, candidate states, flags and UI. A CI lint denylist (`paper`, `PAPER_*`, `paper_only`, `simulated_route`, and similar legacy identifiers) runs over `app/customer/**`, API schemas and dashboard strings and fails the build on any match.

## 3. Principles

1. **Safety before signal.** Any risk-increasing action requires every gate to pass. Any risk-reducing action needs only its own authority and takes a fast path.
2. **LLMs advise, deterministic code decides.** No LLM output reaches a broker. LLM agents emit schema-validated envelopes; deterministic components size, validate and route.
3. **Fail closed for entries, fail safe for exposure.** Missing or stale data blocks new risk. It never blocks protective exits.
4. **One immutable snapshot per cycle**, hashed and referenced by every artifact.
5. **Everything is reconstructable** from snapshot to fill and beyond.
6. **Mode is server-side state**, never a client payload.

## 4. Customer Modes and Plan Tiers

| | Pro | Elite |
|---|---|---|
| Accounts monitored | 1 | Multiple |
| Symbols | Single-symbol focus | Multi-symbol + portfolio |
| Agents | Technical, Regime, News, Sentiment, Confidence, Financial, Watchdog, Guardian, Rescue | Full council incl. portfolio/correlation analysis |
| Weighting | Regime weights | Regime + bounded adaptive agent-health weights |
| Rescue | Standard policies | Advanced/custom policies |
| Audit history | Standard retention | Extended retention |
| LIVE_DEMO | Yes | Yes |
| LIVE_EXECUTION | Eligible after gates (see 11) | Eligible after gates (see 11) |

Tier controls capability breadth. LIVE_EXECUTION eligibility is controlled by account gates, not by tier alone.

## 5. Core Architecture

```text
Market / News / Sentiment / Account / Broker / System Health
                         |
                         v
                  Snapshot Builder  (immutable, hashed, TTL-stamped)
                         |
                         v
                  Specialist Agents  (bounded latency, schema-validated)
                         |
                         v
                 General Coordinator
                         |
                         v
              Confidence + Conflict Layer
                         |
                         v
                 Decision Candidate
        BUY / SELL / WAIT / EXIT / REDUCE
                         |
                         v
                  Capital Guardian   (veto authority)
                         |
                         v
              Deterministic Risk Core (sizing, SL/TP, limits)
                         |
                         v
                  Execution Gateway
        (idempotency, pre-trade checks, kill switches)
                         |
                         v
                    Mode Router
                 /               \
           Demo Adapter     Production Adapter
                 \               /
                         v
             Order Manager + Reconciler
                         |
                         v
                Position Monitor
                         |
                         v
                   Rescue Agent  --(risk-reducing fast path)--> Execution Gateway
                         |
                         v
             Notification + Audit
```

The Rescue fast path is a direct, pre-authorized route to the Execution Gateway for risk-reducing actions only (`REDUCE`, `EXIT`, `PROTECT`, `HALT`).

## 6. Authority Model

| Component | May do | May never do |
|---|---|---|
| Specialist agents | Emit signals/evidence | Size trades, touch credentials, call broker |
| Trader Agent | Propose structured candidate | Bypass Guardian/Risk Core, hold credentials |
| Coordinator | Merge evidence, produce candidate | Override a Guardian veto or a critical Watchdog block |
| Capital Guardian | Veto entries, request reduction | Initiate new risk |
| Deterministic Risk Core | Compute size, SL/TP, validate limits | Be overridden by any agent or LLM |
| Rescue Agent | Emit `HOLD/REDUCE/EXIT/PROTECT/HALT` | Open, add to or reverse positions |
| System Watchdog | Raise blocks, trigger `HALT` | Choose direction |
| Execution Gateway | Sole path to adapters | Accept unsigned/unvalidated intents |
| Customer | Pause, disable live, manual close | Change mode via API payload |

**Asymmetry rule:** risk-reducing actions need one authority; risk-increasing actions need all gates. When Rescue and Coordinator disagree, the more risk-reducing action wins.

## 7. Specialist Agents

**Technical Analyst.** Consumes price/indicator/structure features. Outputs trend, momentum, support/resistance context, multi-timeframe agreement, direction candidate, confidence contribution, blockers.

**News Intelligence Agent.** Consumes timestamped news/event data. Outputs relevance, impact class, affected symbols, freshness, direction bias where justified, risk flags. Returns `UNAVAILABLE` instead of inventing content. Treats all news text as untrusted input (see 16, prompt-injection controls).

**Sentiment Analyst.** Outputs sentiment regime, extremes, divergence from price, confidence contribution, and a source-quality score.

**Market Regime Agent.** Classifies: trending, ranging, volatile, illiquid, event-driven, session-transition. Output drives coordinator weights and entry policy (for example, no new entries in `illiquid`).

**Trader Agent.** Turns council evidence into a structured candidate (direction, thesis, invalidation level, intended horizon). Sizing and final SL/TP come from the Risk Core.

**Capital Guardian.** Independent capital-protection authority: exposure, drawdown, concentration, correlated risk, session limits, stop integrity, margin headroom, and live-specific limits (see 10.4).

**Confidence Agent.** Calibrated confidence from evidence quality and history (see 9). Never the sole safety control.

**Financial Monitor.** Balance, equity, realized/unrealized P&L, drawdown, margin level, exposure, concentration, account anomalies (unexpected balance change, unknown positions, margin call proximity).

**System Watchdog.** Feed freshness, connector state, MT5/API health, latency, duplicates, stale snapshots, clock skew, execution failure rate, reconciliation drift.

**General Coordinator.** Combines outputs, resolves conflicts by regime, applies health weights, records dissent, emits one decision candidate with full rationale path.

**Rescue Agent.** Independent of the Trader Agent, with its own inputs and its own thesis-invalidation logic (see 12).

## 8. Agent Contract

```json
{
  "agent": "technical",
  "snapshot_id": "uuid",
  "snapshot_hash": "sha256",
  "config_version": "string",
  "timestamp": "ISO-8601",
  "status": "OK|DEGRADED|UNAVAILABLE",
  "signal": "LONG|SHORT|WAIT|NEUTRAL",
  "confidence": 0.0,
  "evidence": [{"id": "string", "type": "string", "summary": "string", "source_ts": "ISO-8601"}],
  "blockers": [{"code": "string", "severity": "INFO|WARN|CRITICAL", "detail": "string"}],
  "data_quality": {"fresh": true, "score": 0.0, "max_input_age_ms": 0},
  "latency_ms": 0,
  "criticality": "ADVISORY|SAFETY_CRITICAL"
}
```

Rules:
- Envelope validated against a strict schema. Invalid output is treated as `UNAVAILABLE`.
- `snapshot_id` mismatch invalidates the output.
- Agents receive only normalized state required for their role. No credentials, no order APIs.
- Each agent has a hard timeout. A timeout produces `UNAVAILABLE`, not a retry loop inside the cycle.

## 9. Snapshot Semantics, Decision Logic, Confidence

### 9.1 Snapshot

Immutable per cycle, containing: symbol/timeframe; bid/ask/last/spread; market and snapshot timestamps; volatility and liquidity proxies; technical and regime features; relevant news/event state; sentiment state; account state; open positions and pending orders; portfolio exposure; system/connector health; `config_version`; `snapshot_hash`.

Each snapshot has a **decision TTL** (default a few seconds, configurable per timeframe). A candidate that reaches the Execution Gateway after its TTL is discarded and re-evaluated, never executed late.

### 9.2 Decision Logic

1. Validate snapshot freshness, identity, hash.
2. Collect specialist outputs with bounded latency.
3. Exclude `UNAVAILABLE` from directional weight; record failures.
4. If any `SAFETY_CRITICAL` agent is `UNAVAILABLE`: entries blocked, exits allowed.
5. Apply regime weights, then bounded agent-health weights (Elite).
6. Detect conflicts and evidence concentration (correlated sources counted once).
7. Produce candidate `BUY / SELL / WAIT / EXIT / REDUCE` with the rule/weight path.
8. Confidence Agent calibrates.
9. Capital Guardian evaluates.
10. Risk Core computes size and SL/TP and validates limits.
11. Execution Gateway runs pre-trade checks, then the Mode Router dispatches.
12. Position Monitor and Rescue Agent continue after entry.

### 9.3 Confidence Calibration

Inputs: agreement, independence, freshness, quality, agent health, regime suitability, historical calibration bucket, contradictory-evidence penalty. Minimum thresholds for a high-confidence label require multiple independent supporting factors and no unresolved critical blocker. Calibration is tracked per bucket (for example, do 80% decisions realize about 80% quality) and drifts trigger a confidence cap until recalibrated.

Adaptive weight bounds (Elite): each agent's health weight is clamped to a configured range (for example 0.5x to 1.25x of baseline) and can never lift a `DEGRADED` agent above its baseline.

## 10. Live Execution (new)

### 10.1 Execution Gateway

The single entry point to any broker adapter. Nothing else has adapter access.

Every order intent carries: `intent_id` (idempotency key), `trace_id`, `customer_id`, `account_id`, `mode`, `snapshot_id`, `decision_id`, action, symbol, size, order type, SL, TP, max slippage, expiry, and a signature from the Risk Core. Unsigned or expired intents are rejected.

**Pre-trade checks (deterministic, all must pass for risk-increasing intents):**
1. Signature and TTL valid; `intent_id` not previously used.
2. Account mode and eligibility match the server-side record.
3. Kill switches clear (global, customer, account, symbol).
4. Watchdog reports healthy feed, connector and clock.
5. Spread, liquidity and volatility within entry limits; not inside a blocked news window.
6. Stop-loss present and valid; broker minimum stop distance respected.
7. Size within per-trade, per-symbol, per-account and portfolio limits; margin headroom sufficient.
8. Live limits (10.4) not breached.
9. No conflicting open or pending order on the same symbol/direction (duplicate-signal guard).
10. Account state reconciled within tolerance (see 10.3).

### 10.2 Order Lifecycle

Explicit state machine, persisted on every transition:

```text
CREATED -> VALIDATED -> SUBMITTED -> ACKNOWLEDGED -> PARTIALLY_FILLED -> FILLED
                    \-> REJECTED           \-> CANCEL_REQUESTED -> CANCELLED
SUBMITTED -> UNKNOWN -> (reconcile) -> ACKNOWLEDGED | REJECTED | FILLED
FILLED -> POSITION_OPEN -> CLOSE_REQUESTED -> CLOSED
```

Rules:
- **No blind retries.** A timeout moves the order to `UNKNOWN`. The reconciler queries broker state by `intent_id`/magic/comment before any resubmission. This prevents double execution.
- **Protective stops are broker-side** wherever the venue supports it, placed atomically with entry or immediately after fill. If the SL cannot be confirmed within a bounded window, the position is closed or flattened per policy and the customer is alerted.
- **Slippage guard:** fills outside `max_slippage` trigger an alert, and if the adverse deviation breaches policy, an immediate reduce/exit evaluation.
- **Partial fills** are handled explicitly: remaining quantity is cancelled or re-evaluated against a fresh snapshot, never auto-chased.
- **Rejects** are classified (transient, permanent, account-level). Repeated rejects raise a Watchdog block and an operator alert.

### 10.3 Reconciliation

- Continuous position/order/balance reconciliation between ATLAS state and broker truth (event-driven plus periodic).
- Any drift (unknown position, missing SL, size mismatch, unexpected balance change) raises `CRITICAL` and blocks new entries on that account until resolved.
- Positions not created by ATLAS are flagged as `EXTERNAL` and are never modified without explicit customer consent.
- End-of-day reconciliation report stored with the audit trail.

### 10.4 Live Safety Envelope

Independent of and stricter than demo defaults. All values configurable per account, with conservative platform defaults and hard ceilings the customer cannot exceed:

- Max risk per trade (% equity), max open risk, max daily loss, max weekly loss, max drawdown from peak.
- Max positions, max exposure per symbol, max correlated exposure (Elite portfolio view).
- Max orders per minute and per day; cooldown after consecutive losses.
- Session/time windows and news blackout windows.
- **Circuit breakers:** breach of daily loss or drawdown limit moves the account to `ENTRIES_HALTED` (exits still permitted) and notifies the customer. Resuming requires an explicit customer action, and after a drawdown breach, a cooldown.
- **Kill switches** at four levels: global (operator), customer, account, symbol. Activation cancels working orders, blocks entries, and applies the configured position policy (`HOLD_WITH_STOPS` or `FLATTEN`). Kill switches are checked on every intent, not cached beyond a very short TTL.

### 10.5 Live Enablement and Eligibility

`LIVE_EXECUTION` requires all of:
1. Verified customer identity and account ownership.
2. Production broker account linked with least-privilege credentials (trade permission only, no withdrawal capability).
3. Signed risk disclosure and explicit acknowledgment that automated real-money execution is enabled, with the configured limits shown.
4. Completed minimum LIVE_DEMO/shadow history on the same configuration (see 14).
5. Step-up authentication (MFA re-challenge) at enablement.
6. Limits configured and within platform hard ceilings.
7. Operator or automated eligibility check passed (account type, jurisdiction, product permissions).

Enablement is a server-side state transition with an audit record. The customer may **disable live instantly** at any time; disable takes effect on the next gateway check and cancels working entry orders.

**Staged ramp:** new live accounts start in `LIVE_LIMITED` with reduced size caps and tighter loss limits for a defined period or trade count, then step up only after criteria are met (no reconciliation drift, no critical incidents, calibration within bounds).

### 10.6 Production Adapter Isolation

- Separate service/process, separate network policy, separate credentials vault path from the demo adapter.
- Credentials retrieved by the adapter at call time from a secrets manager, never placed in agent prompts, logs, snapshots, or the client. Rotation supported without redeploy.
- The adapter exposes a narrow interface: `submit`, `modify_sl_tp`, `cancel`, `close`, `query`. No arbitrary broker passthrough.
- Demo and production adapters share a common interface and are exercised by the same contract tests. Configuration cannot point the demo adapter at a production endpoint (startup assertion on endpoint class).
- Production endpoints are separate routes and separately authorized. `mode` is derived from the server-side account record, not from request bodies or headers.

## 11. Conflict Resolution

Examples (all auditable with the inputs and rule/weight path):
- Strong technical LONG plus high-impact conflicting news: reduce confidence or `WAIT` per event policy.
- Technical LONG plus weak-quality sentiment SHORT in a trending regime: technical retains greater weight.
- Multiple stale agents: `WAIT` regardless of directional agreement.
- Watchdog reports broken feed, timestamp drift or broker fault: no new execution until cleared; exits still permitted.
- Rescue `EXIT` versus Coordinator `BUY`: `EXIT` wins.
- Guardian veto: final for entries, cannot be overridden by confidence.

## 12. Position Monitor and Rescue Agent

**Position Monitor** tracks per position: entry, current price, SL/TP state, unrealized P&L, time in trade, distance to invalidation, thesis status, broker-side stop confirmation.

**Rescue triggers** (examples, all configurable): thesis invalidation, adverse volatility/spread expansion, high-impact news against the position, correlation/exposure spike (Elite), drawdown acceleration, stop integrity failure, feed/broker degradation, reconciliation drift, approaching margin call.

**Actions**
- `HOLD`: no change, reason logged.
- `PROTECT`: tighten or restore stop, move to break-even under policy.
- `REDUCE`: partial close to a target exposure.
- `EXIT`: full close.
- `HALT`: block new entries for the account/symbol and escalate.

**Degraded-mode duty:** if the council is unavailable but positions are open, Rescue continues on a minimal deterministic rule set (stop integrity, max loss, margin) so open exposure is never unmonitored. If Rescue itself is down, the Watchdog raises a critical alert and entries are blocked; the customer is told open positions rely on broker-side stops.

Rescue actions are executed via the risk-reducing fast path and are never delayed by council latency.

## 13. Notifications

Event-driven, deduplicated, and each links to the matching dashboard state and trace:
- New decision candidate
- Order submitted / acknowledged / filled / rejected / partially filled
- Execution confirmation (demo and live, clearly labeled by mode)
- Position state change
- Rescue intervention
- Risk rejection or Guardian veto
- Circuit breaker or kill switch activation
- Reconciliation drift or unknown-order event
- System degradation affecting the account
- Live enablement, disablement, limit changes, and login-from-new-device on live accounts

Severity tiers (INFO / ACTION / CRITICAL) and channel routing (in-app, push, email, SMS/messaging for CRITICAL). Delivery failures for CRITICAL alerts are retried and escalated to the operator. Live-mode notifications are visually and textually distinct from demo.

## 14. Reliability and Validation

### 14.1 Shadow Mode
Runs the full path to a decision without dispatching orders. Records the decision, hypothetical entry with a realistic fill model (spread, slippage, latency), outcome, and whether Rescue would have intervened. Required before enabling a new strategy/configuration in LIVE_DEMO, and required before LIVE_EXECUTION.

### 14.2 Replay Engine
Historical snapshots replay through the same contracts and coordinator: high-impact news, spread spikes, gaps, regime changes, reversals, stale data, connector disconnects, duplicate signals, conflicting agents, rapid drawdown, partial fills, order timeouts (`UNKNOWN` handling), and reconciliation drift. Deterministic agents produce identical outputs for identical snapshot and config. LLM agents are replayed from recorded outputs, with a separate evaluation harness for model changes.

### 14.3 Live Promotion Gates
LIVE_EXECUTION eligibility criteria (configurable thresholds, evaluated automatically and reviewed by an operator):
- Minimum duration and decision count in LIVE_DEMO on the same config.
- Zero unresolved reconciliation drift and zero duplicate-execution incidents.
- Rescue and kill-switch drills passed on the production adapter in a sandbox/test environment.
- Calibration within tolerance across confidence buckets.
- Agent availability and latency within SLO.
- Drawdown and stop-integrity metrics within limits.

Passing gates does not guarantee profitability. It only demonstrates operational safety.

### 14.4 Agent Health Score
Per agent: availability, latency, stale-input rate, error rate, disagreement rate, calibration quality, contribution quality. Health influences weight within bounds but never masks an unavailable safety-critical component.

### 14.5 Model and Config Governance
Every agent model, prompt and config is versioned. Changes go through shadow, then LIVE_DEMO, then live rollout with canary accounts and instant rollback. `config_version` is stamped on every decision.

### 14.6 Observability
**Customer dashboard:** positions, symbol, entry, current price, SL/TP, status, confidence, council agreement, risk state, Rescue status, mode badge (`DEMO` / `LIVE`), circuit breaker state, recent notifications, and an execution timeline per order.

**Operator observability:** agent latency and failures, stale data, adapter state, order state-machine counts (especially `UNKNOWN`), reconciliation drift, kill-switch state, audit trace IDs, replay/shadow results, calibration and health dashboards, alerting SLOs.

## 15. Data and Isolation

- Every customer-scoped record carries `customer_id`, `account_id`, `mode`.
- Row-level isolation enforced at the data layer, not only in handlers. Cross-tenant tests in CI.
- Demo and live data are partitioned by `mode` and never joined in customer-facing queries.
- Audit records are append-only, hash-chained (each record references the previous hash), retained per tier, and tamper-evident. Operator access to audit is itself audited.
- Broker credentials live only in the secrets manager. Agents, prompts, logs, snapshots and traces never contain them. Log redaction is tested.
- PII and account identifiers are minimized in LLM prompts (use stable pseudonymous IDs).

## 16. Security

- **Prompt injection:** news, sentiment and any external text are treated as untrusted data, delimited from instructions, length-limited, and never able to alter tool access or risk parameters. Agent outputs must pass schema validation; free text cannot cause execution.
- **AuthN/AuthZ:** step-up auth for live enablement, limit increases and credential changes. Role-based operator access with least privilege.
- **Rate limiting** and abuse controls on customer endpoints. Demo cycle trigger is throttled.
- **Change control** for kill-switch and limit ceilings (dual-control for operators).
- **Incident response:** documented runbooks for stuck orders, drift, adapter outage, feed corruption, and credential compromise, including a procedure to freeze all live accounts.

## 17. API Surface

```text
# Customer (mode derived server-side from the authenticated account)
GET  /api/v2/customer/account
GET  /api/v2/customer/positions
GET  /api/v2/customer/orders
GET  /api/v2/customer/orders/{intent_id}
GET  /api/v2/customer/decisions/latest
GET  /api/v2/customer/agents/status
GET  /api/v2/customer/alerts
GET  /api/v2/customer/rescue/status
GET  /api/v2/customer/limits
PUT  /api/v2/customer/limits                 (within platform ceilings; step-up for increases)
POST /api/v2/customer/cycle/demo
POST /api/v2/customer/entries/pause          (customer kill-switch: halt entries)
POST /api/v2/customer/positions/{id}/close   (manual close, always permitted)

# Live execution (separate router, separate authorization scope)
GET  /api/v2/live/eligibility
POST /api/v2/live/enable                     (step-up auth + signed acknowledgment)
POST /api/v2/live/disable
POST /api/v2/live/killswitch                 (customer-level)
GET  /api/v2/live/reconciliation/status

# Internal / operator
POST /api/v2/internal/replay
POST /api/v2/internal/killswitch             (global/account/symbol, dual-control)
GET  /api/v2/internal/audit/{trace_id}
GET  /api/v2/internal/reconciliation/{account_id}
GET  /api/v2/internal/health/agents
```

Notes: no endpoint accepts a `mode` field that changes execution target. Live routes require the account's server-side state to be `LIVE_ENABLED`. Manual close and entry-pause are always available regardless of system health.

## 18. Proposed Code Layout

```text
app/
  customer/
    accounts/
    agents/
      contracts.py
      base.py
      technical.py
      news.py
      sentiment.py
      regime.py
      trader.py
      capital_guardian.py
      confidence.py
      financial_monitor.py
      system_watchdog.py
      coordinator.py
      rescue.py
      council.py
    realtime/
      snapshot.py
      cycle.py
      conflict.py
      weighting.py
      ttl.py
    execution/
      gateway.py            # idempotency, pre-trade checks, signature verify
      intents.py            # signed order intent schema
      order_state.py        # persisted state machine
      reconciler.py
      killswitch.py
      circuit_breakers.py
      live_eligibility.py
      mode_router.py
      adapter_base.py       # shared interface + contract tests
      demo_adapter.py
      production_adapter.py # isolated, least-privilege
    monitoring/
      position_monitor.py
      notifications.py
    validation/
      shadow.py
      replay.py
      calibration.py
      health.py
      promotion_gates.py
    api/
      customer.py
      live.py
      internal.py
  core/
    mt5/
    risk/
    audit/
    auth/
    market_data/
    secrets/
  legacy/
tests/
  contracts/ risk/ execution/ isolation/ replay/ chaos/ lint_denylist/
```

## 19. Migration Strategy

1. Freeze the legacy path.
2. Identify verified reusable core components.
3. Build v2 contracts, snapshot layer and council independently.
4. Deterministic unit tests for Guardian, Risk Core, Gateway, order state machine before any adapter integration.
5. Add shadow and replay validation, including execution fault scenarios.
6. Integrate LIVE_DEMO through the demo adapter and Gateway.
7. Add customer dashboard and notifications.
8. Validate isolation, fault handling, rescue behavior, kill switches and reconciliation.
9. Build the production adapter and Live Enablement flow behind a feature flag. Exercise in a broker sandbox/test environment.
10. Internal live pilot with company-owned capital, then invited customers in `LIVE_LIMITED`, then general availability as promotion gates are met.
11. Remove legacy simulation modules from the customer runtime and enforce the CI denylist.
12. Delete legacy code in a separate cleanup change after v2 passes acceptance.

## 20. Acceptance Criteria

Core:
- No customer API or dashboard path exposes legacy simulation terminology (CI denylist passes).
- All agents conform to the shared contract; invalid outputs degrade to `UNAVAILABLE`.
- Same-cycle artifacts reference one snapshot ID and hash.
- Stale or missing critical data yields a safe non-entry decision.
- Guardian and Risk Core are independently testable.
- Rescue is independent of the Trader Agent and reacts to post-entry changes, including when the council is down.
- Customer isolation tests prevent cross-account access.
- Replay covers all listed abnormal scenarios; deterministic agents replay identically.
- Calibration buckets and agent-health metrics persist.
- Notifications link to matching state/trace.
- Existing verified core tests still pass.
- Audit trace reconstructs snapshot, agent outputs, coordinator result, risk result, order lifecycle and monitoring outcome, and verifies the hash chain.

Live execution:
- No LLM or agent code path can reach a broker adapter except via the Gateway with a signed, unexpired intent.
- Duplicate intents never produce duplicate orders (idempotency tests, including timeout and `UNKNOWN` recovery).
- Every live entry has a confirmed broker-side stop, or is closed within the configured window.
- Reconciliation detects and blocks on injected drift (unknown position, missing SL, size mismatch).
- Kill switches at all four levels halt entries within the defined latency, cancel working orders, and apply the position policy.
- Circuit breakers trigger on daily loss and drawdown limits, and require explicit resume.
- Demo adapter cannot be configured against a production endpoint; production adapter cannot run with demo credentials.
- Mode cannot be changed by any client payload. Live enablement requires step-up auth and signed acknowledgment.
- Credentials never appear in logs, prompts, snapshots, traces or client responses (redaction tests).
- Live promotion gates evaluate automatically and block ineligible accounts.
- Chaos tests pass: broker disconnect mid-order, feed freeze, clock skew, duplicate fills, partial fills, rejected stop placement.
- LIVE_DEMO end-to-end test passes through the demo adapter with no legacy flow. LIVE pilot passes end-to-end in a sandbox/test environment before any real capital.

## 21. Non-Goals

- Rewriting unrelated billing or marketing code.
- Letting an LLM directly call broker order APIs.
- Guaranteeing trading profitability or returns.
- Treating confidence as a substitute for deterministic capital/risk validation.
- Deleting legacy code before v2 passes acceptance.
- Custody of customer funds or withdrawal capability of any kind.

## 22. Open Decisions for Owner Review

1. Default live risk ceilings (per-trade %, daily loss %, drawdown %) and who may raise them.
2. `HOLD_WITH_STOPS` vs `FLATTEN` as the default kill-switch position policy.
3. Minimum shadow/LIVE_DEMO duration and decision count for live eligibility.
4. Regulatory and jurisdictional review of automated execution on customer accounts (licensing, disclosures, suitability). This should be confirmed with legal counsel before any live customer onboarding.
5. Broker/venue scope for launch (MT5 only vs additional venues) and whether the venue supports server-side stops and OCO.
6. Notification channels for CRITICAL events (SMS/messaging provider).

