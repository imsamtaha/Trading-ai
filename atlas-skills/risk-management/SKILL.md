---
name: risk-management
description: Apply ATLAS deterministic risk controls to paper-trade candidates, including direction validation, stop/target validity, risk percentage, position sizing, and minimum risk/reward. Use before any paper execution.
license: Apache-2.0
metadata:
  author: ATLAS
  version: "1.0.0"
---

# Risk Management

## Workflow
1. Require a TRADE_CANDIDATE.
2. Re-run the deterministic ATLAS risk engine.
3. Reject invalid direction, prices, or risk settings.
4. Require approved risk/reward and bounded position size.
5. Return PAPER_CANDIDATE only after approval.

## Rules
Risk rejection is final for the current setup. Never let an AI-generated rationale override the deterministic risk gate.


## Educational reference: Risk Management tut V3

The user-uploaded 40-page study guide is indexed in `knowledge/risk_management_v3.json`.
Read it using `app.intelligence.risk_reference.risk_study_topics()` or `risk_study_topic(key)` when explaining a topic to a human or discussing a PAPER scenario. The Council records the read-only reference metadata in `risk_education_reference` for traceability.

The guide discusses Trading Trident, drawdown recovery, reward/risk, sizing, leverage, candlesticks, and discretionary trade management. It is study material, not ATLAS risk policy. Never copy its leverage or risk-per-trade suggestions into live defaults, bypass protective stops, or override an existing risk rejection. The uploaded PDF itself is not hosted or committed here.
