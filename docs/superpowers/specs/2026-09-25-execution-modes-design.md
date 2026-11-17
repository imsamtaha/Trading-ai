# ATLAS Execution Modes Design

## Goal
Separate ATLAS execution by actor and account so the owner retains a private paper workflow while customers use isolated MT5 demo or real-account workflows.

## Modes
- `PAPER`: owner-only. Never calls a broker order API.
- `LIVE_DEMO`: customer mode bound to that customer's MT5 demo account. Uses real broker market data and demo-account execution only.
- `LIVE_EXECUTION`: customer production mode bound to that customer's MT5 real account. The application architecture supports it, but validation and automated tests must never send a real-money order.

## Execution context
Every execution request is bound to immutable context containing `user_id`, `account_id`, `mode`, and `is_owner`. No process-wide execution mode may authorize a customer request. Account credentials and broker sessions must be resolved by `(user_id, account_id)` and may not be supplied by arbitrary request parameters after authentication.

## Authorization rules
1. `PAPER` requires `is_owner=True` and is hidden/rejected for customers.
2. `LIVE_DEMO` requires a customer-owned account whose MT5 `trade_mode` is DEMO.
3. `LIVE_EXECUTION` requires a customer-owned account whose MT5 `trade_mode` is REAL.
4. A user/account mismatch fails closed.
5. Unknown/contest account modes fail closed for customer execution.
6. Risk Manager, execution gate, emergency stop and audit logging remain mandatory for customer execution.
7. Explicit authorization/confirmation is required before any production execution request reaches the broker adapter.

## Isolation
All account lookup, positions, orders, audit records and emergency-stop state are scoped by `user_id + account_id`. No customer can enumerate, select or execute against another customer's account. Owner paper state is stored separately from customer broker state.

## Broker boundary
`MT5Broker` remains the Windows broker adapter. Mode validation occurs before broker execution and is repeated against broker-reported account metadata. `dry_run` is not used as user identity or authorization. Paper execution uses a dedicated paper adapter/service rather than toggling a customer's MT5 broker into dry-run.

## Safety and risk
Existing confidence/risk gating stays fail-closed. Production execution also requires customer authorization, account ownership, REAL account verification, trade permission, emergency-stop clear state and audit creation. Errors or unavailable metadata block execution.

## UI/API
Owner workspace exposes Paper privately. Customer workspace exposes Live Demo and Live Execution status for the authenticated customer's own account only. APIs return explicit mode and gate status without exposing credentials. Live Execution controls must not imply that a trade was sent unless the broker confirms it.

## Validation
Add regression tests for owner/customer mode access, account isolation, DEMO/REAL/CONTEST mapping, emergency stop, missing authorization, cross-account access and broker failures. Run focused tests and the full pytest suite. Windows MT5 integration verifies connect, account metadata, quotes, restart/reconnect and gates without sending a real-money order.

## Deployment definition of done
The version is complete only when code is reviewed/merged, CI is green, the Windows ATLAS service starts successfully, the Cloudflare tunnel routes the production hostname to the correct local service, and `/`, `/dashboard`, and `/health` are verified externally. DNS/mail records unrelated to the web route must remain untouched.
