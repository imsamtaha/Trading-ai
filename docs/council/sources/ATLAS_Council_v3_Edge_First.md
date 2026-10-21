# ATLAS Council v3: Edge-First Design

"Old" = the v2.1 council (ten specialist agents, coordinator, confidence layer, safety architecture).
"New" = v3, redesigned to maximize measured, cost-adjusted, risk-adjusted performance.

**What "best performing" means here:** the highest net-of-cost risk-adjusted return that survives out-of-sample testing, with a bounded worst case. It does not mean guaranteed profit. No design can promise that. v3 is built so that every component must prove it earns its place, and so that a lack of edge shows up early and cheaply instead of in customer accounts.

---

## 1. The core difference

| | Old (v2.1) | New (v3) |
|---|---|---|
| Design goal | Safe, auditable decision pipeline | Measurable edge on top of the same safety layer |
| What the council is | Ten agents whose outputs are merged | A portfolio of validated alpha models, each judged by its own P&L |
| How a decision is made | Weighted evidence, then a confidence score | Expected net value after costs, with abstain as the default |
| Direction source | Technical, sentiment and news agents (LLM-heavy) | Deterministic quantitative models, versioned and backtestable |
| Role of LLMs | Contribute directional signal | Classify news/events and flag risk only. Never call direction alone |
| Correlated evidence | Counted once by a rule | Measured statistically. Weights come from decorrelated marginal contribution |
| Confidence | Calibrated score from many inputs | A meta-labeler trained on realized trade outcomes |
| Costs | Spread filter | Explicit cost model. A trade needs positive expected edge after spread, slippage, fees |
| Sizing | Fixed risk % with limits | Volatility-targeted, fractional-Kelly capped, drawdown-scaled |
| Adaptivity | Health-based weights | Champion/challenger with decay detection and automatic demotion |
| Validation | Shadow and replay for safety | Walk-forward, purged validation, baselines, multiple-testing correction |
| Agent count rule | More agents = more coverage | Every agent must show positive marginal contribution or it is removed |
| Failure mode caught | Operational failures | Operational failures and no-edge / edge-decay failures |

**Unchanged and kept from v2.1:** Execution Gateway, signed intents, idempotency, order state machine, reconciliation, kill switches, circuit breakers, production adapter isolation, customer isolation, audit hash chain, notification design, and the Rescue Agent's independence. Performance work sits on top of that layer and never bypasses it.

---

## 2. Design thesis

Trading performance is roughly:

`net performance = (edge per trade) x (number of independent bets) - costs, then scaled by sizing and limited by survival`

The old council optimized safety and explainability. It did not say where edge comes from, so more agents did not reliably add performance. v3 attacks each factor directly:

1. **Edge:** small set of distinct, individually validated alpha sources.
2. **Breadth:** several uncorrelated sleeves and symbols, because breadth raises risk-adjusted return more reliably than a better single signal.
3. **Costs:** trade only when expected edge clears costs by a margin.
4. **Sizing:** size by conviction and volatility, cap by Kelly fraction, cut in drawdown.
5. **Survival:** the v2.1 safety envelope.

---

## 3. Architecture

```text
Market / News / Account / Broker / System Health
                   |
                   v
       Point-in-Time Feature Store  (no look-ahead, versioned)
                   |
        +----------+-----------+-----------------+
        v          v           v                 v
   Alpha Sleeves  Regime     Event/News       Cost & Liquidity
   (quant models) Model      Classifier(LLM)  Model
        |          |           |                 |
        +----------+-----------+-----------------+
                   |
                   v
            Meta-Labeler
   (P[trade is net-profitable | signal, regime, context])
                   |
                   v
     Allocator / Ensemble  (decorrelated, uncertainty-aware)
                   |
                   v
   Expected Net Value Gate  (abstain unless EV > hurdle)
                   |
                   v
         Sizer  (vol target, fractional Kelly, drawdown scaling)
                   |
                   v
        Capital Guardian -> Deterministic Risk Core
                   |
                   v
   Execution Gateway (v2.1)  ->  Mode Router  ->  Demo / Production
                   |
                   v
     Position Monitor + Rescue Agent (v2.1, upgraded with exit model)
                   |
                   v
   Outcome Labeler -> Learning Loop -> Champion/Challenger Registry
```

---

## 4. Components (replaces the ten-agent council)

### 4.1 Alpha Sleeves
Each sleeve is a deterministic, versioned model with a written hypothesis for why it earns money and when it should fail.

| Sleeve | Hypothesis | Expected to fail when |
|---|---|---|
| Trend / momentum | Persistent moves continue across timeframes | Range-bound, choppy markets |
| Mean reversion | Overextended moves revert to a short-term mean | Strong trends, event shocks |
| Volatility breakout | Compression precedes expansion | Low liquidity, false-break sessions |
| Event-driven (uses News Classifier) | Scheduled and unscheduled events create tradable dislocations | Ambiguous or already priced-in events |
| Carry / macro (optional, later) | Slow structural premia | Regime breaks |

Each sleeve outputs: signal, strength, expected holding period, invalidation level, expected gross edge in R-multiples, and its own confidence from trailing realized performance. Sleeves are trained and evaluated independently, and their returns are tracked as separate streams.

### 4.2 Regime Model
Statistical model (for example change-point detection and a hidden-state model on volatility, trend strength, liquidity) rather than a text classification. Outputs regime probabilities, not a single label. Its job is to gate sleeves (turn off mean reversion in strong trends) and to feed the meta-labeler. It is evaluated on whether gating improves sleeve results out-of-sample.

### 4.3 Event/News Classifier (the only LLM-centric agent)
- Input: timestamped news and event data, treated as untrusted text.
- Output: structured fields only: event type, affected symbols, surprise magnitude estimate, novelty (already priced in or not), risk flag, timestamp.
- Never outputs BUY/SELL. Its output is a feature for the meta-labeler and a blocker/flag for entries.
- Evaluated on labeled outcomes: does adding its features improve the meta-labeler out-of-sample? If not, it is reduced to risk flagging only.

### 4.4 Cost & Liquidity Model
Predicts spread, slippage and fill probability for the intended size, time and venue from live spread, depth proxies, session, volatility and recent fills. Fed continuously by real execution data (predicted vs realized slippage). Its output is a per-trade expected cost in R.

### 4.5 Meta-Labeler
The key upgrade to "confidence". A model trained on historical sleeve signals with labels from realized outcomes (triple-barrier: take-profit / stop / time), predicting the probability that this specific signal, in this context, is net-profitable. Features: sleeve outputs, regime probabilities, event features, cost estimate, time of day, recent sleeve performance. It replaces the decorative confidence score with a probability that is directly checked against results (calibration curve, Brier score, reliability by bucket).

### 4.6 Allocator / Ensemble
Combines sleeves by **marginal contribution to portfolio risk-adjusted return**, not by vote. Weights come from trailing out-of-sample performance, correlation between sleeve return streams, and estimation uncertainty (shrink toward equal-risk weights when data is thin). Highly correlated sleeves share one risk budget. Weight changes are rate-limited to avoid chasing noise.

### 4.7 Expected Net Value Gate
```text
EV_net = P(win) * avg_win_R - (1 - P(win)) * avg_loss_R - expected_cost_R
trade only if: EV_net > hurdle  AND  lower confidence bound of EV_net > 0
```
`P(win)` comes from the meta-labeler. Default is **abstain**. Most cycles should produce no trade. The hurdle rises when the model is uncertain, data is degraded, or the regime is unfamiliar.

### 4.8 Sizer
- Volatility targeting: position size scaled so each trade risks a target amount in R regardless of instrument volatility.
- Fractional Kelly cap: size never exceeds a small fraction (start at a quarter of Kelly, computed from the lower confidence bound of edge, not the point estimate).
- Drawdown scaling: risk per trade shrinks as drawdown deepens and recovers gradually.
- Portfolio scaling: correlated open risk shares one budget (Elite).
- All outputs are still passed to the Capital Guardian and Risk Core, which can only reduce or reject.

### 4.9 Capital Guardian, Risk Core, Gateway, Watchdog
Unchanged from v2.1.

### 4.10 Rescue Agent (upgraded)
Same independence and authority as v2.1, plus an **adverse-excursion / exit model** trained on trade history: given the position's path so far, regime and event state, estimate the probability the trade recovers versus deteriorates, and recommend `HOLD / PROTECT / REDUCE / EXIT`. Exit quality is measured separately (did Rescue interventions improve outcome versus holding to stop?). Interventions that do not beat "hold to stop" are retuned or turned off.

### 4.11 Outcome Labeler and Learning Loop
- Labels every decision, including abstentions (what would have happened), with the triple-barrier method and costs included.
- Scheduled retraining on rolling windows, with drift detection on features and on live-versus-backtest performance.
- New model versions enter as challengers only (section 6).

---

## 5. Evaluation Protocol (how "best" is decided)

**Baselines every new council must beat, net of costs:**
1. Cash / do nothing.
2. Simple trend-following on the same instruments and risk.
3. Random entries with identical sizing, stops and costs (checks whether results beat luck and risk management alone).
4. The old v2.1 council, in shadow on the same data and time window.

**Method**
- Point-in-time data only. Purged, embargoed walk-forward validation. A final holdout period touched once.
- Realistic fill model: spread, slippage, latency, partial fills, commission, and stress cases at 1.5x to 2x costs.
- Multiple-testing correction (for example deflated Sharpe) because many variants get tried.
- Bootstrap confidence intervals on expectancy and drawdown. Report the lower bound, not the mean.
- Results sliced by regime, session, symbol and event/no-event to find where it works and where it breaks.
- Minimum sample sizes before any claim (see gates).

**Metrics**
- Net expectancy per trade (R), profit factor, hit rate, average win/loss.
- Sortino, Calmar, max drawdown, time under water, tail losses.
- Turnover, cost as % of gross edge, predicted vs realized slippage.
- Calibration (Brier, reliability by bucket) for the meta-labeler.
- Rescue value: outcome with intervention vs hold-to-stop.
- Sleeve and agent **ablation**: portfolio result with and without each component.

---

## 6. Champion / Challenger and Decay Control

- The running configuration is the **champion**. Any new model, sleeve, prompt or weight scheme is a **challenger** running in shadow on live data.
- Promotion requires beating the champion out-of-sample with statistical support, not a single good stretch.
- **Ablation rule:** every sleeve and agent must show positive marginal contribution net of costs. Components that do not are removed. This is how the council stays small and effective.
- **Decay monitor:** a sleeve whose live performance falls below its backtest confidence band has its risk budget cut automatically, then is suspended pending review.
- Every model has a version, training window and data hash for reproducible replay.

---

## 7. Promotion Gates (starting thresholds, to be tuned with your data)

| Stage | Requirement |
|---|---|
| Research | Beats all baselines out-of-sample net of costs, under stressed costs, positive lower confidence bound on expectancy |
| Shadow | At least several hundred resolved decisions and several regime changes. Live-vs-backtest gap within tolerance. Calibration within tolerance |
| LIVE_DEMO | Operational safety gates from v2.1 plus performance stability, realized slippage within model, no drift incidents |
| LIVE_LIMITED | Reduced size caps, tighter loss limits, live realized costs match model, no critical incidents |
| LIVE_EXECUTION | Step up only when limited-stage criteria are met over a defined period |

Demotion is automatic when live results fall outside the expected band or a safety gate fails.

---

## 8. What Improves Performance, Ranked by Expected Impact

1. **Cost awareness and abstention.** Avoiding negative-net trades often beats finding better ones.
2. **Breadth from decorrelated sleeves and symbols.**
3. **Risk-aware sizing and drawdown scaling.** Big drivers of the risk-adjusted result.
4. **Regime gating of sleeves.**
5. **Meta-labeling** to filter weak signals.
6. **Exit management** via the Rescue exit model.
7. **Event features** from the LLM classifier (valuable only if ablation confirms it).

## 9. Honest Limits

- Nothing here guarantees profit. Markets change, and a sleeve that worked can stop working. The design's advantage is detecting that quickly and cutting risk.
- If no sleeve beats the baselines out-of-sample after costs, the correct output is that ATLAS should not trade live yet. The system is designed to surface that answer.
- Backtests overstate live results. Expect a gap and size accordingly.
- Real-money automation on customer accounts carries licensing, disclosure and suitability obligations that vary by jurisdiction. Get legal review before live onboarding.

## 10. Build Order

1. Point-in-time feature store, outcome labeler, cost model, and baseline strategies with the evaluation harness. **Build the measuring stick first.**
2. Two or three sleeves (trend, mean reversion, breakout) plus regime model. Prove or reject each with ablation.
3. Meta-labeler and EV gate. Prove it improves net expectancy.
4. Allocator and sizer. Prove the risk-adjusted improvement.
5. Event/News Classifier as a challenger feature source.
6. Rescue exit model.
7. Shadow, then LIVE_DEMO, then LIVE_LIMITED, using the v2.1 safety layer throughout.
8. Retire any component that fails ablation. Keep the council as small as the evidence allows.

