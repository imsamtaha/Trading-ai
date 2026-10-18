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
