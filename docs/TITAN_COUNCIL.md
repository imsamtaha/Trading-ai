# TITAN Council v1.0

TITAN is ATLAS's unified, paper-only SMC scalping profile for BTCUSD, ETHUSD and explicitly approved high-liquidity major crypto markets. The ATLAS multi-asset council continues to handle its own market coverage.

## Paper assessment

- `GET /agent/titan/policy` returns the published policy.
- `POST /agent/titan/analyze` evaluates a reviewed snapshot and returns a single TITAN assessment. See the request schema in `/docs`. The ATLAS public-analysis gate applies in dashboard-only mode.
- Submit the asset, time-zone-aware timestamp, price, session, and a quality verdict for each labeled chart. Review 4H direction, 1H structure, 15M liquidity, 5M setup and 1M entry in that order. Confirm that the charts refer to the same instrument and observation. A chart passes when it clearly shows structure, includes the time frame and price scale, and retains the relevant areas.
- Review market regime, both sides of liquidity, the directional sweep, CHOCH, BOS, displacement, order block, FVG and volume. Record MSS, mitigation blocks and premium or discount areas when relevant. Check the news calendar and any asset or regulatory news before marking the news gate clear. Longs need a sell-side sweep. Shorts need a buy-side sweep.
- Report paper equity, current period losses, month-to-date peak-to-trough drawdown, loss streak and active positions using a consistent accounting window. The endpoint trusts supplied observations. Source verification and ongoing account monitoring belong to the operator or upstream system.
- Scores use the specified binary weights. A or S is a prerequisite. With every weighted confirmation mandatory, a complete v1.0 setup scores 100.
- Reward-to-risk is measured to the first target after estimated round-trip fees and slippage. Size is a paper risk budget divided by loss per unit before lot rounding. Use consistent account-currency point values. An unpassed gate produces WAIT and a reason list. A limit breach produces a STOP capital-preservation verdict.
- Review candidate BUY or SELL outputs before recording them. Hold at most two active paper positions, preferably one. Move stops only with confirmed structure, keep protection at least as tight as before, and avoid adding to losing positions or raising risk after entry.

## Journal and review

| Stage | Record |
| --- | --- |
| Pre-trade | Date, asset, session, regime, directional bias, liquidity target and sweep, CHOCH, BOS, order block, FVG, R:R, risk, grade, entry reason, confidence |
| Active | Entry, stop, targets, current R:R, volume behavior, unexpected events, management notes |
| Settled | Win/loss/breakeven, P&L, expected and actual R, maximum drawdown, exit quality, compliance, mistakes, lessons |
| Process | Score structure, liquidity, risk, entry timing, management and exit quality from 0–10 each. Sum the six scores out of 60 and grade rule compliance independently of P&L. |

Weekly, calculate win rate, average realized R, profit factor, drawdown and risk compliance from settled paper trades. Compare best and worst setups and record what to repeat or eliminate. Monthly, assess capital growth, drawdown, setup and session performance, violations, the top three winners and losers, the most frequent mistake and improvements. Report unavailable metrics as unavailable. The assessment returns a journal-ready decision for the paper operator to record. Submit the settled trades in a chosen period with its opening equity to `POST /agent/titan/review`. Use `weekly` or `monthly` and supply process scores in policy order. The endpoint computes summaries from the supplied slice, including monthly rankings by realized R. Record decisions about what to repeat, eliminate or improve in the review notes.
