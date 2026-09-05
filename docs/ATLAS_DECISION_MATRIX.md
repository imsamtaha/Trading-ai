# ATLAS Decision Matrix v1.0

## Purpose

ATLAS uses a deterministic scoring layer between market-analysis modules and the LLM explanation layer. The score identifies directional opportunity; the risk gate has final veto authority.

## Component weights

| Component | Weight |
|---|---:|
| Market structure | 20 |
| Trend / MTF alignment | 15 |
| Support / resistance | 10 |
| Liquidity | 10 |
| Momentum | 10 |
| Volume / participation | 10 |
| Volatility | 10 |
| Price action confirmation | 5 |
| Macro / fundamentals | 10 |
| **Total** | **100** |

Each evidence component is normalized to `[-1, +1]`:

- `-1` strongly bearish
- `0` neutral or unavailable
- `+1` strongly bullish

Long and short scores are calculated independently. Missing evidence contributes zero; it is never fabricated.

## Directional gate

`directional_edge = long_score - short_score`

A directional bias requires an absolute edge of at least 15 points.

- Positive edge: LONG candidate
- Negative edge: SHORT candidate
- Absolute edge below 15: NEUTRAL / NO TRADE

Higher-timeframe conflict can veto the setup. A counter-trend setup needs substantially stronger evidence and must not be created by a lower timeframe alone.

## Conviction

### HIGH

- Score >= 75
- Directional edge >= 25
- At least 3 independent confluence factors
- Risk/reward >= 1.5
- No hard risk veto

### MODERATE

- Score >= 60
- Directional edge >= 15
- At least 2 meaningful confluence factors
- Risk/reward >= 1.5
- No hard risk veto

### LOW

A surviving directional setup that does not meet the moderate thresholds is LOW conviction. A single-indicator setup cannot become high conviction.

## Hard risk vetoes

Any of these produces `NO_TRADE`:

- stale market data
- critical data missing
- undefined invalidation
- extreme volatility when the setup is not explicitly designed for it
- imminent major event risk
- chasing an extended entry
- higher-timeframe conflict when not sufficiently compensated by evidence
- account risk above 2%
- undefined risk/reward
- risk/reward below 1.5

The numerical score never overrides a risk veto.

## Position sizing

Default account risk is 1%, with a hard engine maximum of 2%:

`position_size = account_equity * risk_fraction / (abs(entry - stop) * contract_multiplier)`

Leverage is intentionally absent from the sizing formula. Leverage affects margin and liquidation sensitivity and belongs to the independent execution/risk layer.

## Timeframes

Primary execution/analysis timeframes:

- 5m
- 15m
- 30m
- 1h

Structural context:

- 4h
- 1d
- 1w

The scoring engine accepts the timeframe explicitly so the upstream MTF engine can supply properly aggregated evidence. It does not pretend that one timeframe is multi-timeframe evidence.

## Architecture boundary

```text
Market feeds
  -> technical / structure / regime / macro engines
  -> normalized evidence [-1, +1]
  -> ATLAS scoring engine
  -> risk gate
  -> trade plan
  -> execution permission

LLM layer = explanation and scenario communication, not hidden score manipulation.
```

## Validation requirement

The engine is deterministic and therefore suitable for unit tests, backtests, paper trading, and audit logs. Thresholds and weights must be validated against out-of-sample historical data before any live execution is authorized.
