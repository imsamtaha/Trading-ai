# ATLAS Trading Council: Nine-Seat PAPER Governance Contract

Status: **DRAFT / NOT DEPLOYED**. Source: owner's proposed 9-seat System Prompt, 18 Nov 2026. Preserve the legacy ATLAS Council, ledger, demo MT5 connector and risk controls; this branch introduces a **separate, non-executing** model of that prompt for review.

## System identity and mode

ATLAS produces **simulated/paper decision-support recommendations only**. The live safety flags stay `ATLAS_LIVE_TRADING=false` and `ATLAS_DASHBOARD_ONLY=true`. This module neither places live nor demo broker orders and never claims an order was filled. Every output is explicitly labelled `SIMULATED/PAPER RECOMMENDATION`, with `mode=paper`.

Core coverage includes gold (XAUUSD), silver (XAGUSD), major equity indices (US500, US30, NAS100), select large-cap equities, WTI crude (USOIL/WTI), Brent crude (UKOIL/BRENT), natural gas (NGAS), and EUR/USD (EURUSD). XRP and SOL (including their USD/USDT symbols) are **satellite crypto** with a 5/5 conviction gate for directional previews. The PAPER shortlist ranks gold and equities first, commodities and FX next, and limits crypto to one directional preview per four eligible non-crypto directional previews in the batch. WAIT and veto records consume no slots and remain visible. Supported standalone bias timeframes are 5m, 15m, 30m, and 1h.

**Schema clarification:** The contract uses **`commodity`** for silver, crude oil, and natural gas. Confirm downstream dashboard clients accept this enum before merging.

## Nine seats

1. **Chair / Portfolio Manager:** final simulated verdict, conviction (1–5), position-size percentage within the *already approved* paper Risk limit, cited drivers and one-paragraph rationale. May justify overrides of other seats, **never** Risk.
2. **Macro Analyst:** instrument-specific bullish/bearish/neutral bias, relevant driver and next event horizon; emphasize real yields, DXY and central banks for gold; breadth, sectors and earnings for equities. No invented news.
3. **Market Structure Analyst:** higher-timeframe regime, levels/liquidity, invalidation, session behavior; gold London/New York overlap and equity gap/opening-range evidence only if verified.
4. **Quant Validator:** research confidence, pattern hit rate, R:R, sample size, provenance, regime/earnings drift warnings; n<30 explicitly annotated anecdotal.
5. **Risk Manager:** final `APPROVE`, `VETO`, or `CONDITIONAL` with reason; VETO also requires a minimum change before reevaluation. APPROVE requires explicit PASS in daily-loss, open-risk, correlation, position-size and event-exposure checks. **These are supplied assertions; the library does not replace the authoritative account-level Risk Engine.**
6. **Execution Specialist:** after Risk APPROVE only; drafts a PAPER entry, stop, targets and order type, plus spread/slippage/session hazards. No MT5 calls.
7. **News / Sentiment Analyst:** calendar, events, Fed-speak, earnings and sentiment skew; distinguish fresh/verified records from unverified summaries.
8. **Red Team:** independent contrarian challenge after a PAPER execution plan; objection and failure condition required. "No objection" without an explicit justification is rejected.
9. **Evaluator:** weekly retrospective read-only scorecard using only settled PAPER outcomes, by PM conviction and asset class. Does not vote on current proposals or invent fills.

## Deliberation stages

- Phase A: Macro, Market Structure, Quant and News submit separately against a shared `snapshot_id`; submissions are sealed before Risk. The stage APIs do not pass another seat's report to the submitting seat. **True isolation between different LLM calls must be enforced by the future orchestration layer**.
- Phase B: Risk checks the proposal and the portfolio. Risk VETO skips PAPER execution and goes directly to Chair for an explicit VETOED verdict. CONDITIONAL remains NO TRADE until reviewed and approved.
- Phase C: on explicit APPROVE only, Execution submits a structured PAPER plan with validated stop/target direction.
- Phase D: Red Team challenges the plan; then Chair finalizes, citing the drivers.
- Phase E: Evaluator independently scores past settled PAPER outcomes **weekly**, not per trade.

## Output contract

The `finalize()` result includes these top-level keys:

```
instrument, asset_class, timeframe, timestamp, mode, verdict, conviction,
position_size_pct, entry, stop, take_profit, seats, chair_rationale,
decision, confidence, risk_pct, evidence_issues
```

`seats` contains `macro`, `market_structure`, `quant`, `risk`, `execution`, `news_sentiment`, and `red_team`. The Chair is represented by `verdict` and `chair_rationale`; the Evaluator is a **separate weekly output**. Risk veto and conditional decisions result in null entry and stop, empty take-profit and size 0. No orders or funding actions are possible.

- `decision` is `BUY`, `SELL`, or `WAIT`. Missing, unverified, stale, or conflicting required evidence yields `WAIT` with the affected inputs identified in `evidence_issues`. A Risk veto also yields `WAIT`, preserves the `VETOED` verdict, and can be finalized without waiting for Chair.
- Every required report carries a timezone-aware ISO-8601 `timestamp` between the verified snapshot time and the evaluation time. The snapshot and reports may be at most one configured chart interval old. `finalize(as_of=...)` supports replay with an explicit timezone-aware evaluation time and defaults to current UTC.
- A directional decision requires the Market Structure seat's matching `setup_direction` (`LONG` or `SHORT`), written `liquidity_evidence` and `smc_confirmation`, News/Sentiment's explicit `event_risk_acceptable: true`, and the Red Team's `material_conflict: false`. The nearest execution target must offer at least 3:1 reward to risk using the submitted entry and stop.
- `confidence` is `UNSCORED` because the Chair's 1–5 conviction is an ordinal assessment. `risk_pct` is 0 for `WAIT` and null for a directional preview pending an account-risk percentage from an authoritative source.

## Acceptance gates before any integration

- Run `python -m pytest -q tests/test_nine_seat_paper_council.py` on a clean checkout.
- Confirm veto cannot be overridden, nonapproved plans never appear, low-sample/base-rate warnings are explicit, out-of-timeframe coverage fails closed, and unverified market snapshots cannot produce directional proposals.
- Confirm the real source of account-level risk and paper fills. This module accepts structured reports, but **does not collect actual macro/equity news, price streams, independent LLM seat outputs or verified account metrics**.
- Validate historical data, output schema clients, and weekly Evaluator on true settled PAPER logs. Never interpret synthetic fixtures as measured trading accuracy or performance.
- Do not merge, publish, deploy, modify model weights, execute a broker order or turn on real-money trading without a separate reviewed release.

The implementation is intentionally **a safe policy/validation prototype**, not a claim that nine LLM agents are already running.
