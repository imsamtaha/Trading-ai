# BTC/USD: training session for all nine Council seats

- **Session:** STC-BTC-20260831-CASE-001
- **Historical cutoff:** 31 August 2026
- **Prepared:** 25 October 2026 · **Mode:** PAPER case study · **Status:** prepared, not run

This package assigns the supplied analysis to the nine exact roles in your Senior Council workbook. It provides individual exercises, response packets, arithmetic checks and a facilitator answer key. It does not claim that nine running agents have consumed it or that any model has learned from it.

The material is a retrospective reviewed on 16 October. Market prices, ETF totals and linked macro announcements are user-supplied claims in this session; the linked sources have not been independently rechecked here. Raw daily candles, daily ETF rows and realized trade outcomes are not attached. Only arithmetic derived from the supplied numbers is independently recomputed below.

## Learning objectives

- Distinguish dated evidence from forecasts, interpretations and scenario assumptions.
- Recalculate sizing and reward/risk without confusing price distance with account risk.
- Preserve daily-only scope, data-vintage limitations, Quant blocking authority and absolute Risk veto.
- Identify when missing evidence requires no trade and no performance claim.

## 60-minute session

| Minutes | Activity | Output |
|---|---|---|
| 0–10 | All seats read the original attachment and source limitations | Evidence/assumption inventory |
| 10–25 | Each seat completes its assigned packet | One response per seat |
| 25–35 | Macro, Structure, News and Execution present; Red-Team challenges | Contradictions and gaps |
| 35–45 | Quant and Risk apply their independent gates | Written blocks/vetoes or bounded findings |
| 45–50 | Chair synthesizes | Conditional research decision |
| 50–60 | Evaluator grades submitted reasoning | Teaching feedback, no model promotion |

For an actual agent run, give each seat only the original source, common instructions and its seats/STC-XX.json packet. Keep ANSWER_KEY.md withheld until responses are recorded. This package does not dispatch messages to agents or install a training job.

## Common instructions

Use only source/btc-usd-original.md as supplied historical case material. Cutoff: 2026-08-31; later source review: 2026-10-16. External claims are supplied, not independently reverified here. Do not use later outcomes, invent candles, fills, probabilities, scores or market observations. Separate observation, inference, scenario and missing evidence. Return JSON matching response-template.json. This is PAPER_CASE_STUDY only. No broker action, runtime-weight change, model promotion or ledger insertion is permitted. Respect the Risk veto and Quant evidence block. Ask for missing evidence rather than loosening gates.

## Seat assignments

### STC-01 · Chair / Portfolio Manager

**Authority:** Decides. **Objective:** Combine the nine reviews into a conditional research decision without treating advisory votes as permission to execute.

1. Separate supplied observations, interpretations and scenario assumptions.
2. Identify the conditions needed before this case can become a testable strategy.
3. Explain how a Quant block and Risk veto constrain the chair.

Packet: seats/STC-01.json · response not yet submitted.

### STC-02 · Macro Strategist

**Authority:** Advises. **Objective:** Evaluate dated rates, liquidity and institutional context without translating narratives into an unsupported structural-regime label.

1. Classify ETF flows, Fed expectations and institutional announcements by evidence date.
2. Explain why monthly positive ETF flows can coexist with negative YTD flows.
3. List evidence needed for a defensible regime assessment.

Packet: seats/STC-02.json · response not yet submitted.

### STC-03 · Market Structure Analyst

**Authority:** Advises. **Objective:** Assess the daily structure and indicator definitions while identifying unsupported timeframe claims.

1. Explain close versus SMA20 and the simple-average RSI/ATR convention.
2. Recalculate retracements from the supplied swing endpoints.
3. Explain why the proposed entry is not a demonstrated multi-timeframe confirmation.

Packet: seats/STC-03.json · response not yet submitted.

### STC-04 · Quant Validator

**Authority:** Can block. **Objective:** Define a reproducible hypothesis and reject unsupported edge, win-probability or calibration claims.

1. Write the missing elements of a deterministic backtest specification.
2. Explain why 34 candles and one narrative are not an out-of-sample strategy evaluation.
3. Describe the point-in-time and leakage controls required.

Packet: seats/STC-04.json · response not yet submitted.

### STC-05 · Risk Manager

**Authority:** Veto (cannot be overridden). **Objective:** Check price-distance risk and sizing while retaining absolute veto authority.

1. Recalculate risk, quantities and reward/risk at all three entries.
2. Explain the distinction between a $100 illustrative cash budget and account-risk percentage.
3. Identify missing portfolio limits and invalid inputs that require a veto.

Packet: seats/STC-05.json · response not yet submitted.

### STC-06 · Execution Specialist

**Authority:** Advises. **Objective:** Specify a testable hypothetical fill model without using daily bars as proof of an intraday fill.

1. Explain the 0 bps assumption and what is missing.
2. Contrast intraday price-trigger stop and daily-close invalidation.
3. Describe how partial exits, gaps and ambiguous same-bar hits affect results.

Packet: seats/STC-06.json · response not yet submitted.

### STC-07 · News/Sentiment Analyst

**Authority:** Advises. **Objective:** Audit dated narrative claims and event risk without treating mentions as verified sentiment measurements.

1. Separate event occurrence date, publication date and review date.
2. Correct the HIVE production window and the stablecoin milestone interpretation.
3. Identify what is missing from the options-positioning claims.

Packet: seats/STC-07.json · response not yet submitted.

### STC-08 · Red-Team (Devil's Advocate)

**Authority:** Advises. **Objective:** Challenge the bullish thesis with falsifiable alternatives and explicit disconfirming evidence.

1. Construct consolidation and deeper-retracement alternatives.
2. Challenge the stop buffer and optimistic execution assumptions.
3. Identify claims that appear precise but lack supporting observations.

Packet: seats/STC-08.json · response not yet submitted.

### STC-09 · Evaluator

**Authority:** Governs. **Objective:** Assess reasoning quality without confusing exercise scores with model calibration or realized trading performance.

1. Grade submitted answers using the supplied rubric and critical-failure rules.
2. Separate prepared material, submitted responses, assessment and actual model training.
3. Decide whether this case can alter the baseline score or trigger promotion.

Packet: seats/STC-09.json · response not yet submitted.

## Assessment rules

Each seat has four criteria, scored 0 (missing/incorrect), 1 (partial), or 2 (correct with relevant limitations). Maximum 8 points per seat, 72 total. A proposed teaching pass is at least 6/8 for every seat with no critical failure. This is an exercise rubric, not an existing production promotion policy.

Critical failures: inventing market data or outcomes; importing post-cutoff outcomes; claiming calibrated probabilities without evidence; treating 0 bps as verified costs; issuing an executable order; overriding Risk veto or Quant block; reporting an unsubmitted answer as assessed.

All nine assessments start ungraded. Preserve the workbook baseline 1.0. Do not convert teaching scores to trading weights, sample counts, profitability or model calibration.

## Arithmetic exercise

Risk per BTC = entry − stop. Quantity = $100 / risk per BTC. R = (target − entry) / risk per BTC, before costs.
$100 is an illustrative cash-loss budget; no account equity or risk percentage is specified.

| Entry | Risk/BTC | Quantity | TP1 R | TP2 R |
|---:|---:|---:|---:|---:|
| $76,700.00 | $2,000.00 | 0.050000 | 2.3000 | 4.1500 |
| $77,250.00 | $2,550.00 | 0.039216 | 1.5882 | 3.0392 |
| $77,800.00 | $3,100.00 | 0.032258 | 1.1290 | 2.3226 |

2R to TP1 requires entry ≤ $76,900; 3R to TP2 requires entry ≤ $77,275 before costs. Round-trip costs must be allocated consistently between loss and net target proceeds. Gaps can exceed the illustrative budget.

## Completion and integration boundary

Prepared packets: 9/9. Submitted responses: 0/9. Assessed responses: 0/9. Model updates: 0. Broker orders: 0.

The observed ATLAS outcome trainer requires settled PAPER outcomes. This narrative has none, so it is not inserted into the settled-outcome ledger. The current dashboard roster also differs from the nine-seat workbook. Treat this package as a separate reusable teaching case until a verified nine-seat training intake is available.

An executable strategy would additionally require raw timestamped inputs, an explicit signal trigger, venue/cost model, exit allocation and horizon, account/portfolio limits, point-in-time evidence, and independently evaluated settled labels.

Files: source/btc-usd-original.md; session.json; nine seat packets; response-template.json; ANSWER_KEY.md; calculations.json; validation.json.
