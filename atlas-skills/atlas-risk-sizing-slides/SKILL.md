---
name: atlas-risk-sizing-slides
description: Create or update a presentation explaining how a scikit-learn signal (such as social sentiment) flows into Atlas/portfolio risk controls and bounded position sizing. Use when asked to visualize model outputs, quality gates, risk-sizing formulas, governance, testing, or human approval in an explanatory slide deck.
---

# Atlas Risk Sizing Slides

Turn a proposed ML-to-risk integration into an accurate, reviewable presentation. Keep the work scoped to explanatory slides and paper-only scenarios.

## Workflow

1. **Identify the deliverable.** Determine whether the user wants a new deck or edits to a named existing deck. Preserve the user's language and any supplied Atlas/agent architecture. Ask only when missing information would materially alter the integration. Read [the ATLAS architecture](../../docs/ATLAS_STRUCTURE.md) for the Council, Senior Risk, Executive, and Paper boundaries. Treat unverified endpoints and schemas as unknown and label illustrative contracts as proposed.
2. **Use the available presentation workflow.** Follow the presentation tooling available in the current environment for creating, editing, previewing, and delivering the deck. Export a specific format when the user requests it.
3. **Map the decision chain.** Use the content sequence below, adjusting the slide count to scope (normally 5–7 slides; stay within the Slides limit unless asked otherwise):
   - purpose and simulation-only boundary;
   - data/model output contract;
   - quality and freshness gate;
   - baseline risk sizing and bounded model adjustment;
   - risk-governor caps, veto, and human approval;
   - time-based validation, monitoring, audit, and staged rollout.
   A concise cover and closing slide may be added when useful.
4. **Separate facts from placeholders.** Preserve user-provided parameters as user-provided, not as validated settings. Clearly label invented thresholds, formulas, endpoint paths, confidence cutoffs, freshness limits, and adjustment bands as *illustrative only*. Do not claim expected accuracy, profitability, or risk reduction without evidence.
5. **Explain the model output.** When relevant, show score, confidence, sample count, data window/freshness, source coverage/quality, and model version. Include symbol/market and generated timestamp in a proposed payload only if useful. Explain how missing, stale, low-confidence, or unapproved model output is handled by the stated policy; do not silently substitute stale values.
6. **Explain sizing without surrendering risk authority.** Present baseline size as derived from an approved loss budget and loss to invalidation after fees/slippage. If model output modifies size, show the adjustment as bounded and subordinate to approved caps. Do not let sentiment alone create or reverse a trade, increase leverage, exceed risk budget, exposure, liquidity limits, or override the risk governor.
   - If the adjustment depends on trade direction, use a position-aligned score (e.g., sentiment score multiplied by the sign of the proposed position) or explicitly state that the formula is a non-directional illustration. Avoid presenting a formula that implicitly treats a negative sentiment as risk-reducing for both long and short positions.
   - Distinguish an optional adjustment from a required decision input. Apply ATLAS's documented HOLD gate when required decision input is missing, invalid, or stale.
7. **Show paper evaluation.** Describe offline, time-ordered evaluation, out-of-sample and paper testing, comparison with a baseline without sentiment, drift and source-manipulation monitoring, model versioning, audit logs, and human review. Describe an evaluation as complete only when verified.
8. **Create the deck.** Plan the outline before authoring. Use a legible visual style and native slide elements for calculations and diagrams where suitable. Show the direction of information flow and Senior Risk's veto authority.
9. **Verify and deliver.** Preview every slide, correct layout and validation issues, and share the deck through the presentation workflow. Summarize the deck and any assumptions in the user's language.

## Default governance framing

- Model output is advisory context or a bounded adjustment input, never an autonomous order.
- The approved risk budget and risk governor remain authoritative; veto results in no approval until resolved.
- Use defined states such as `valid`, `stale`, `low_confidence`, `insufficient_coverage`, and `unapproved_model` only as an illustrative schema unless Atlas confirms them.
- Label training, evaluation, and paper-simulation results with their data source and status.
- Avoid exposing API keys, credentials, or private account data in slides.

## Formula communication pattern

When the user supplies a formula, preserve it and explain its variables. When creating a conceptual example, state assumptions near the formula, bound the factor explicitly, then show post-adjustment caps. For example only:

```text
aligned_score = sentiment_score × position_sign
factor = clamp(1 + adjustment_band × aligned_score × confidence,
               minimum_factor, maximum_factor)
final_size = min(base_size × factor, approved_size_cap, risk_budget_size)
```

Do not insert concrete parameter values unless the user supplied them or explicitly asked for illustrative values. If showing examples, label every such value as unapproved and for illustration only.
