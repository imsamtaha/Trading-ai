---
name: technical-analysis
description: Interpret ATLAS technical indicators including EMA trend, RSI momentum, MACD, ATR, volume state, and support/resistance. Use when technical context is needed for a paper-trade decision.
license: Apache-2.0
metadata:
  author: ATLAS
  version: "1.0.0"
---

# Technical Analysis

## Workflow
1. Require sufficient candles.
2. Use ATLAS `analyze_candles` output.
3. Identify trend, momentum, volatility, and levels.
4. Report conflicts explicitly.

## Rules
Do not invent indicator values. Technical evidence alone is insufficient to authorize a paper trade.
