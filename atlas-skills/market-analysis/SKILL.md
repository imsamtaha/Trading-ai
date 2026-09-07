---
name: market-analysis
description: Analyze ATLAS market data across supported assets and timeframes, combining price context, volatility, trend, and signal state. Use for market-state assessment before any trade consideration.
license: Apache-2.0
metadata:
  author: ATLAS
  version: "1.0.0"
---

# Market Analysis

## Use When
Assessing current market state, directional bias, volatility, or whether conditions justify deeper trade evaluation.

## Don't Use When
Do not bypass deterministic ATLAS engines or fabricate unavailable market data.

## Workflow
1. Load candles from the ATLAS market-data layer.
2. Run technical and structure analysis.
3. Read signal-engine output.
4. Return WAIT unless a validated candidate exists.

## Rules
Treat engine outputs as authoritative. Never convert uncertainty into a trade merely to increase activity.
