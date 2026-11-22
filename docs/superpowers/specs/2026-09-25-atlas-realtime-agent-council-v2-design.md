# ATLAS Realtime Agent Council v2

## Purpose

Build a new customer-first ATLAS decision subsystem that replaces paper-trading-oriented decision flow with a real-time multi-agent intelligence path for LIVE_DEMO and a separately controlled production execution interface. The system must continuously observe market, news, sentiment, account, execution and system state, form a current decision from the latest evidence, monitor positions after entry, notify the customer, and activate a rescue path when conditions deteriorate.

## Scope

This design covers the new customer runtime only. Existing legacy orchestration remains frozen for reference until the new customer path reaches validation targets. Reusable components such as MT5 connectors, deterministic risk calculations, authentication, market-data adapters and audit utilities may be retained where verified.

Paper-trading concepts are removed from the customer runtime. Terms such as `paper_only`, `PAPER_CANDIDATE`, paper routing and paper execution must not be part of the new customer API or dashboard.

## Customer Modes

- `LIVE_DEMO`: automated analysis, monitoring, alerts and demo-account execution against live market data.
- `LIVE_EXECUTION`: production execution interface isolated from demo state and enabled only for eligible, authorized production accounts. The decision system itself remains identical; account mode changes the execution adapter, not the intelligence path.

## Plan Tiers

### Pro
- Single-account real-time monitoring.
- Technical, market-regime, news, sentiment, confidence, financial and system agents.
- Position monitoring and Rescue Agent.
- Notifications and live customer dashboard.

### Elite
Includes Pro plus:
- Full agent council.
- Multi-symbol and portfolio-level monitoring.
- Correlation and exposure analysis.
- Adaptive agent weighting based on recent agent health and data quality.
- Deeper audit history and advanced rescue policies.

## Core Architecture

```text
Market / News / Sentiment / Account / MT5 / System Health
                         |
                         v
                  Snapshot Builder
                         |
                         v
                  Specialist Agents
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
                  Capital Guardian
                         |
                         v
              Deterministic Risk Core
                         |
                         v
                    Mode Router
                 /               \
          LIVE_DEMO         LIVE_EXECUTION
                 \               /
                         v
                Position Monitor
                         |
                         v
                   Rescue Agent
                         |
                         v
             Notification + Audit
```

## Specialist Agents

### Technical Analyst
Consumes live price/indicator/structure features and outputs trend, momentum, support/resistance context, multi-timeframe agreement, direction candidate, confidence contribution and blockers.

### News Intelligence Agent
Consumes timestamped news/event data and outputs event relevance, expected impact class, affected symbols, evidence freshness, direction bias where justified, and risk flags. It must degrade to `UNAVAILABLE` instead of fabricating when data is missing.

### Sentiment Analyst
Consumes available crowd/market sentiment inputs and outputs sentiment regime, extremes, divergence from price action and confidence contribution.

### Market Regime Agent
Classifies the current state such as trending, ranging, volatile, illiquid or event-driven. Its output changes how the coordinator weights technical and sentiment evidence.

### Trader Agent
Transforms current council evidence into a structured trade candidate. It never bypasses Capital Guardian or deterministic risk checks and never has direct broker credentials.

### Capital Guardian
Independent capital-protection authority. Evaluates exposure, drawdown, concentration, position sizing, correlated risk, session limits and stop integrity. It may veto a new trade or request exposure reduction.

### Confidence Agent
Produces calibrated confidence from evidence quality, agreement, freshness and historical calibration. Confidence is not a decorative probability and must not be the sole safety control.

### Financial Monitor
Tracks balance, equity, realized/unrealized P&L, drawdown, margin, open exposure, portfolio concentration and account-state anomalies.

### System Watchdog
Tracks feed freshness, connector state, MT5/API health, latency, duplicate events, stale snapshots, clock skew and execution failures.

### General Coordinator
Combines specialist outputs, resolves conflicts according to current market regime, applies agent-health weighting, records dissent and produces one structured decision candidate.

### Rescue Agent
Independent from the Trader Agent. Monitors open positions and system state after entry and may emit `HOLD`, `REDUCE`, `EXIT`, `PROTECT` or `HALT` when market or system conditions materially deteriorate.

## Agent Contract

Every specialist returns a deterministic envelope:

```json
{
  "agent": "technical",
  "timestamp": "ISO-8601",
  "status": "OK|DEGRADED|UNAVAILABLE",
  "signal": "LONG|SHORT|WAIT|NEUTRAL",
  "confidence": 0.0,
  "evidence": [],
  "blockers": [],
  "data_quality": {
    "fresh": true,
    "score": 0.0
  },
  "latency_ms": 0
}
```

Agents must not expose broker credentials or call MT5 order placement directly.

## Snapshot Semantics

Each decision cycle uses one immutable snapshot containing:
- symbol and timeframe
- bid/ask/last price and spread
- market timestamp and snapshot timestamp
- volatility and liquidity proxies
- technical features
- market-regime features
- relevant news/event state
- available sentiment state
- account state
- open positions
- portfolio exposure
- system/connector health

All agent outputs in a cycle must reference the same snapshot ID. Stale or mixed-time inputs reduce confidence or block the decision.

## Decision Logic

The coordinator does not use simple majority voting.

1. Validate snapshot freshness and identity.
2. Collect specialist outputs with bounded latency.
3. Exclude `UNAVAILABLE` outputs from directional weight while recording the failure.
4. Apply market-regime-dependent weights.
5. Apply agent-health weights.
6. Detect conflicts and evidence concentration.
7. Produce `BUY`, `SELL`, `WAIT`, `EXIT` or `REDUCE` candidate.
8. Confidence Agent calibrates the confidence score.
9. Capital Guardian evaluates capital state.
10. Deterministic Risk Core validates executable parameters.
11. Mode Router dispatches to the account-specific execution adapter.
12. Position Monitor and Rescue Agent continue evaluation after entry.

## Conflict Resolution

Examples:
- Strong technical LONG + high-impact conflicting news => reduce confidence or `WAIT` depending on event policy.
- Technical LONG + sentiment SHORT during a trending regime => technical evidence may retain greater weight if sentiment quality is weak.
- Multiple stale agents => `WAIT` regardless of directional agreement.
- Watchdog reports broken feed, timestamp drift or MT5 fault => no new execution until the fault clears.

Every conflict resolution must be auditable with the inputs and rule/weight path used.

## Confidence Calibration

Confidence is derived from:
- evidence agreement
- evidence independence
- data freshness
- data quality
- agent health
- market regime suitability
- historical calibration bucket
- contradictory evidence penalty

A high confidence score must require multiple independent supporting factors and no unresolved critical blocker. Calibration statistics are tracked by confidence bucket so that 80% decisions can be evaluated against realized decision quality over time.

## Reliability and Validation Layer

### Shadow Mode
Before enabling automated demo execution for a new strategy/configuration, decisions can run in shadow mode. The system records the decision, hypothetical entry, subsequent outcome and whether Rescue Agent intervention would have occurred.

### Replay Engine
Historical snapshots can be replayed through the same agent contracts and coordinator to validate behavior against:
- high-impact news
- spread spikes
- gaps
- volatility regime changes
- trend reversals
- stale data
- API/MT5 disconnects
- duplicate signals
- conflicting agents
- rapid drawdown

Replay output must be deterministic for deterministic agents given the same snapshot and configuration.

### Agent Health Score
Track per-agent:
- availability
- latency
- stale-input rate
- error rate
- disagreement rate
- calibration quality
- recent decision contribution quality

Health affects weighting but cannot hide an unavailable critical safety component.

### Observability
Customer dashboard exposes current positions, symbol, entry, current price, SL/TP where applicable, status, decision confidence, council agreement, risk state, Rescue status and recent notifications.

Operator observability additionally exposes agent latency, failures, stale data, execution adapter state, audit trace IDs and replay/shadow validation results.

## Notifications

Notifications are event-driven and must include at least:
- new decision candidate
- demo execution confirmation
- position state change
- Rescue intervention
- risk rejection
- system degradation affecting the account

Customer opens the notification into the matching live dashboard state and trace.

## Data and Isolation

Every customer-scoped record carries `customer_id`, `account_id` and `mode`. No account may read or act on another customer's snapshots, positions, credentials, alerts or audit records.

Broker credentials are stored outside agent prompts and logs. Agents receive only normalized account and market state required for their role.

## API Surface

Initial endpoints:

```text
GET  /api/v2/customer/account
GET  /api/v2/customer/positions
GET  /api/v2/customer/decisions/latest
GET  /api/v2/customer/agents/status
GET  /api/v2/customer/alerts
GET  /api/v2/customer/rescue/status
POST /api/v2/customer/cycle/demo
POST /api/v2/internal/replay
GET  /api/v2/internal/audit/{trace_id}
```

Production execution endpoints remain separate from demo endpoints so mode cannot change through a client payload alone.

## Proposed Code Layout

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
    execution/
      mode_router.py
      demo_adapter.py
      production_adapter.py
    monitoring/
      position_monitor.py
      notifications.py
    validation/
      shadow.py
      replay.py
      calibration.py
      health.py
    api/
  core/
    mt5/
    risk/
    audit/
    auth/
    market_data/
  legacy/
```

## Migration Strategy

1. Freeze the existing paper-oriented agent/orchestrator path.
2. Identify reusable verified core components.
3. Build the v2 contracts, snapshot layer and council independently.
4. Add deterministic unit tests before integrating with MT5/demo adapters.
5. Add shadow and replay validation.
6. Integrate LIVE_DEMO first.
7. Add customer dashboard and notifications.
8. Validate isolation, fault handling and rescue behavior.
9. Move old paper-specific modules out of customer runtime and remove paper terminology from customer APIs/UI.
10. Keep legacy code available only until v2 passes acceptance tests, then remove it in a separate cleanup change.

## Acceptance Criteria

The subsystem is not considered complete until all of the following pass:
- No customer API or dashboard path exposes paper-trading terminology.
- All agents conform to the shared contract.
- Same-cycle agents reference one snapshot ID.
- Stale/missing critical data results in a safe non-entry decision.
- Capital Guardian and deterministic risk validation are independently testable.
- Rescue Agent is independent from Trader Agent and can react to post-entry state changes.
- Customer isolation tests prevent cross-account access.
- Replay tests cover at least the defined abnormal-market/system scenarios.
- Confidence calibration buckets and agent-health metrics are persisted.
- Notifications link to the matching customer state/trace.
- LIVE_DEMO end-to-end test succeeds through MT5 demo adapter without legacy paper flow.
- Existing verified core tests remain passing.
- Audit trace reconstructs each decision from snapshot through agent outputs, coordinator result, risk result and execution/monitoring result.

## Non-Goals for This Change

- Rewriting unrelated billing or marketing code.
- Letting an LLM directly call broker order APIs.
- Guaranteeing trading profitability.
- Treating confidence as a substitute for deterministic capital/risk validation.
- Deleting legacy code before v2 passes acceptance criteria.
