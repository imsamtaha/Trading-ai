# ATLAS Execution Guard Agent Spec

## Goal
Add a dedicated execution agent between the advisory decision layer and MT5 execution.
The agent converts an approved council decision into either a safe demo execution or a live trade draft that still requires one explicit human confirmation before broker submission.

## Current codebase anchors
- `app/demo_executive/service.py` already produces deterministic demo-only decisions and stores executive events.
- `app/execution/mt5.py` already validates account mode, SL/TP direction, broker limits, duplicate-risk controls, and a 1% stop-loss risk ceiling before `order_send`.
- `app/mt5_demo/service.py` and its tests already require matching account identity and explicit confirmation for manual live orders.
- `app/users/routes.py` exposes authenticated dashboard state, feature flags, and Owner access.

## Proposed flow
`Council Decision -> Execution Guard Agent -> Risk Gate -> Demo Auto Execute / Live Trade Draft -> MT5 -> Audit Log`

The council output is a structured object with symbol, direction, confidence, rationale, timestamp, proposed SL/TP, and risk context.
The Execution Guard Agent never invents a trade when the council decision is WAIT, stale, incomplete, or internally inconsistent.

## Guard checks
1. Decision is BUY/SELL and confidence meets configured threshold.
2. Market data timestamp is fresh.
3. Stop-loss and take-profit are present and directionally valid.
4. Requested volume satisfies broker min/max/step rules.
5. Projected SL loss is within the existing risk ceiling.
6. Account identity and account mode still match the connected session.
7. Duplicate decision/request IDs cannot execute twice.

## Account-mode behavior
### Demo
For a connected DEMO account, the agent may auto-submit a broker demo order after every guard passes.
Demo auto-execution remains separately feature-gated and auditable.

### Live
For a REAL account, the agent prepares a `TradeDraft` only.
The draft contains symbol, side, volume, SL, TP, confidence, rationale, council evidence, risk result, and expiry.
Broker submission occurs only after an authenticated explicit confirmation for that exact draft.
No blanket confirmation, background autonomous live execution, or reusable approval token is allowed.

## Components
- `app/execution_guard/models.py`: CouncilDecision, GuardResult, TradeDraft, ExecutionEvent.
- `app/execution_guard/service.py`: validates council output, runs guard checks, creates demo execution or live draft.
- `app/execution_guard/routes.py`: authenticated status, evaluate, draft, confirm, and event endpoints.
- Existing `MT5Broker.market_order()` remains the final broker adapter and keeps its current broker/risk checks.
- Existing repository/audit layer stores decision ID, user ID, account fingerprint, outcome, block reason, and timestamps.

## API shape
- `POST /api/execution-guard/evaluate`: evaluate a council decision.
- `GET /api/execution-guard/status`: current state and last outcome.
- `GET /api/execution-guard/events`: user-scoped audit events.
- `POST /api/execution-guard/confirm/{draft_id}`: confirm one live draft only.

All state-changing endpoints require authenticated user context and same-origin/CSRF protection consistent with existing MT5 routes.

## Failure behavior
- Missing/invalid council data -> `BLOCKED`.
- Stale market state -> `BLOCKED`.
- Risk or broker validation failure -> `BLOCKED` with a non-secret reason.
- Account mode/login changes before execution -> `BLOCKED`.
- Expired live draft -> cannot be confirmed.
- Duplicate decision or draft -> idempotent rejection.
- Any MT5 exception -> recorded failure; no automatic retry that could double-submit.

## UI behavior
ATLAS Dashboard adds an `EXECUTION AGENT` sector showing:
- council decision and confidence,
- guard status: READY / BLOCKED / EXECUTED / WAITING CONFIRMATION,
- concise block reason,
- demo execution result or live draft review,
- audit timeline.

No profit claims or certainty language are shown.

## Testing
TDD coverage must include:
- WAIT never reaches broker execution,
- stale/low-confidence/invalid-SL decisions are blocked,
- duplicate IDs never execute twice,
- Demo can auto-execute only when demo execution is enabled,
- Live always creates a draft first,
- Live confirmation is bound to user, account, draft ID, and expiry,
- changed account identity/mode blocks submission,
- projected stop risk above the existing ceiling blocks submission,
- every outcome produces an isolated user-scoped audit event.

## Rollout
1. Implement models/service/tests with fake broker only.
2. Integrate authenticated routes and audit persistence.
3. Add dashboard sector.
4. Run full backend/frontend suites.
5. Keep live broker execution disabled by environment until a separate verified deployment step.
