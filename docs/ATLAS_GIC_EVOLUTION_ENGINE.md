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
Active prompt/weight registry
        |
        v
Existing ATLAS deterministic decision + risk + execution path
```

## Composite score

The evaluator uses:

- 30% risk-adjusted return
- 20% directional accuracy
- 15% calibration
- 15% drawdown control
- 10% regime accuracy
- 10% consistency

All metric inputs are normalized to 0..1.

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
```

## Promotion rule

A prompt candidate is promoted only when its composite score exceeds the
incumbent by at least `min_improvement` (default 0.03). Otherwise it is
reverted.

This first implementation is intentionally shadow-only. Persisted experiment
history, rolling windows, regime cohorts, and scheduled autoresearch can be
layered on without weakening the execution boundary.
