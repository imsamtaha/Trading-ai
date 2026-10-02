# ATLAS Runtime + GIC-style Evolution Engine

## Goal

Add bounded self-improvement to ATLAS without giving the evolution layer broker
or MT5 execution authority.

## Architecture

```text
Market/Context Inputs
        |
        v
Specialist Agents
(technical, macro, news, sentiment, regime, risk)
        |
        v
Evolution scorecards
        |
        +--> composite score
        +--> bounded Darwinian weight (0.30..2.50)
        +--> worst-agent detection
        |
        v
Shadow candidate evaluator
        |
        +--> PROMOTE when improvement >= threshold
        +--> REVERT otherwise
        |
        v
Shadow prompt/weight registry (detached; no runtime consumer)
```

## Composite score

The evaluator uses:

- 30% risk-adjusted return
- 20% directional accuracy
- 15% calibration
- 15% drawdown control
- 10% regime accuracy
- 10% consistency

Finite metric inputs are normalized to 0..1. NaN and infinity are rejected before clamping, including direct Python calls.

## Safety boundary

The evolution package deliberately has:

- no broker dependency;
- no MT5 dependency;
- no order-placement method;
- no ability to alter `ExecutionPolicy`;
- mutation APIs disabled unless `ATLAS_EVOLUTION_WRITES_ENABLED=true`.

The existing risk and execution layers stay authoritative.

## API

Read-only status:

```
GET /evolution/status
```

Write endpoints, disabled by default:

```
POST /evolution/score
POST /evolution/evaluate
```

Enable only in a controlled private runtime:

```
ATLAS_EVOLUTION_WRITES_ENABLED=true
ATLAS_DASHBOARD_ONLY=false
ATLAS_LIVE_TRADING=false
ATLAS_AUTO_EXECUTION_ENABLED=false
```

Both evolution writes and the dashboard-only middleware gate must permit writes.
Keep this configuration private. It does not enable broker orders.

## Promotion rule

A prompt candidate is promoted only when its composite score exceeds the
stored incumbent by at least `min_improvement` (default 0.03), compared at the six-decimal scoring precision. Otherwise it is reverted. For an unrecorded agent only, supplied incumbent metrics bootstrap the comparison.

`GET /evolution/status` exposes per-agent `versions`. Supply `expected_version` in `/evaluate` to reject stale evaluations with HTTP 409. All updates and snapshots are protected by one process-local lock. State is in memory; use a single API process while writes are enabled. A shared persistent registry is required before multi-process evolution writes.

The registry is shadow-only and has no effect on current decisions. `/runtime/status` reports `evolution_influences_decisions=false`; the execution pipeline does not list unused evolution weights.

This first implementation is intentionally shadow-only. Persisted experiment
history, rolling windows, regime cohorts, and scheduled autoresearch can be
layered on without weakening the execution boundary.


## Automatic worker contract

This PR also contains a separate opt-in automatic worker. The runtime switch has only STATUS, OFF, DASHBOARD and DEMO modes; it never enables broker orders. All execution defaults remain disabled.

The coordinator refreshes MT5 account/history and all open positions before the final risk check. Realized daily P&L uses the UTC calendar day and includes trading profit, commission, swap and fees; balance/credit operations do not offset losses. The daily-loss denominator is UTC start-of-day balance, reconstructed from current balance by reversing the full day’s balance-changing deal amounts (including deposits, withdrawals and trading costs; credit is tracked separately by MT5). Intraday cash flows and floating P&L cannot dilute a breached daily-loss limit. A missing or non-positive baseline blocks execution. Balance, credit and account identity are checked again after collection; changes during history/position reads block that cycle rather than combining inconsistent snapshots. Current equity still sizes new trades and aggregate open risk. Open risk is the account-currency loss from the current bid/ask to each position's stop. Unknown history, missing stop protection, non-finite inputs or failed cash-risk calculations block new entries.

The final requested risk is the smaller of `ATLAS_AUTO_RISK_PERCENT` and the candidate's validated `metadata.risk.risk_percent`. The candidate must be qualified and have a current `created_at` Unix timestamp. Original SL/TP levels are preserved and reward/risk is recalculated at the quote. Entry deviation is checked in broker points both in the coordinator and immediately before order submission. Broker lot sizing rounds down; an unaffordable minimum lot is rejected, and cash risk is checked again at the final quote. Cash-risk estimates do not guarantee against gaps/slippage beyond the broker's execution terms.

The worker loads the root `.env` before reading switches. It requires a private analytical provider snapshot selected with `ATLAS_AUTO_CONTEXT_FILE`; no provider is activated by this change. Write snapshots atomically to avoid partial reads. A single JSON snapshot has this schema (values must come from the actual analytical provider):

```json
{
  "symbol": "EURUSD",
  "as_of": 1790967600,
  "source": "your-private-context-provider",
  "macro_score": 0.1,
  "news_score": -0.2,
  "geopolitical_score": 0.0,
  "cross_asset_score": 0.1,
  "reaction_score": 0.2,
  "conflict_score": 0.15,
  "volatility_score": 0.25,
  "event_risk_score": 0.3
}
```

`as_of` is a UTC Unix timestamp, not a permanent configuration value. Directional fields must be finite in [-1,1]; conflict, volatility and event risk must be finite in [0,1]. Missing, malformed, wrong-symbol, future-dated or stale snapshots produce NO_TRADE. Technical evidence is the candidate’s finite confidence in [0,100], divided by 100 and signed by LONG/SHORT direction; qualification alone never upgrades evidence to a perfect score. Missing or invalid candidate confidence also produces NO_TRADE. The existing repository has no connected live macro/news provider; configuring a file path alone does not supply one.

Defaults: context max age 300 seconds (`ATLAS_AUTO_CONTEXT_MAX_AGE_SECONDS`), candidate max age 60 seconds (`ATLAS_AUTO_MAX_CANDIDATE_AGE_SECONDS`), quote max age 30 seconds (`ATLAS_MT5_MAX_QUOTE_AGE_SECONDS`), maximum entry deviation 20 broker points (`ATLAS_AUTO_MAX_ENTRY_DRIFT_POINTS`). Configure the deviation for each instrument's point size; it is not a fixed pip or percentage tolerance.

DEMO keeps `ATLAS_DASHBOARD_ONLY=true` and evolution writes disabled, even when `-Evolution` is supplied. The dashboard allowlist already permits its guarded paper/demo endpoints; general external tool writes remain blocked.
