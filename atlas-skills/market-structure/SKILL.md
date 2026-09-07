---
name: market-structure
description: Interpret ATLAS market-structure output such as swing behavior, structural bias, and confirmation/conflict with technical trend. Use before accepting a directional paper-trade candidate.
license: Apache-2.0
metadata:
  author: ATLAS
  version: "1.0.0"
---

# Market Structure

## Workflow
1. Read deterministic structure-engine output.
2. Compare structural bias with technical trend and signal direction.
3. Flag disagreement as reduced conviction.
4. Prefer WAIT when confirmation is weak.

## Rules
Structure analysis must not override the risk engine or create an order by itself.
