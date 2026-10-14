# ATLAS specialist council

The council separates structural context, entry research and risk authority.
It does not train one model for all three jobs. The customer-agent sales/CSAT
model remains a separate customer-routing component.

| Role | Inputs | Training target | Authority |
| --- | --- | --- | --- |
| Macro Analyst | Policy-rate changes, inflation surprises, genuine order-flow imbalance; publication/vintage timestamps | `structural_regime` | Asset-specific regime context |
| Quantitative Strategist | Trend, momentum, price action, pair spread z-score, transaction costs | Settled `net_return_r` after costs | Entry proposal |
| Risk Executive | Existing risk policy, stop geometry, cash-risk bounds, current portfolio, measured correlations | None | Absolute veto; never a directional vote |

## Decision integration

`build_paper_council` emits two analytical opinions and a separate versioned
Risk Executive verdict. Technical signals and execution quality form one Quant
opinion, avoiding multiple votes for the same evidence. News remains supporting
context. Missing macro inputs return `HOLD` with `DATA_UNAVAILABLE`; news or MT5
tick volume is not substituted for policy data or genuine order flow. Macro
evidence must match the symbol and snapshot and have been available by the
decision time. A regime name never determines an asset direction on its own.

Statistical-arbitrage proposals require snapshot-matched pair research marked
out-of-sample validated and inclusive of costs. This is an input contract, not
a newly implemented pair strategy or proof of profitability.

The root paper monitor evaluates the Risk Executive even when council training
is disabled. Existing sizing, daily-loss and portfolio-risk percentages remain
unchanged. The executive checks a strict boolean policy approval, positive
finite sizing evidence, stop/target geometry and correlation limits. Rejected
or malformed risk cannot be outweighed by analytical confidence or learned
weights. Both aggregation boundaries exclude veto roles from directional votes.

Set `ATLAS_MAX_ABS_CORRELATION` to an owner-selected value in `(0, 1]` before
adding exposure to an existing portfolio. There is no invented default. For
each existing symbol, the producer aligns completed price bars, computes
Pearson correlation of log returns and requires at least 30 adjacent returns
with nonzero variance. Missing, stale, future-dated or incomplete evidence
vetoes the entry. Correlations at or above the absolute cap veto the entry,
including negatively correlated pairs; this policy does not assume hedging
reduces risk. The method is a historical estimate, not a future-loss guarantee.

The root automatic execution coordinator derives its verdict from a fresh
broker portfolio snapshot and current quote. `AtlasExecutionService` requires
the verdict for every enabled entry, plus finite cash-risk and approved-stop
bounds. The broker retains its final account, portfolio-fingerprint, quote and
cash-risk rechecks. The legacy owner-confirmed `/mt5/test-order` route cannot
enter without trusted server risk approval. Paper intents remain non-executable
at the broker gate, and this change does not enable live trading.

The divergent `runtime/private-api` broker does not have the root coordinator's
portfolio/correlation/budget revalidation path. Its real and demo broker entries
therefore fail closed with `RISK_EXECUTIVE_CONTEXT_UNAVAILABLE`; manual trading
reports inactive. This also covers its direct manual/DemoExecutor entry path.
Account reads and the separate position-closing method remain available.
Restoring private entries requires implementing trusted portfolio risk approval,
not setting a caller approval flag. Its legacy paper monitor has not been
migrated to the new council.

## Independent offline training

```bash
python scripts/train_council_specialist.py --role macro_analyst --csv /path/to/observed_macro.csv --confirmed-observed
python scripts/train_council_specialist.py --role quantitative_strategist --csv /path/to/settled_quant.csv --confirmed-observed
```

Each input contains the role's feature columns, target, `snapshot_at`,
`available_at`, `label_available_at`, and `source`. All timestamps require
explicit timezones. `available_at` is the latest availability time of the
feature evidence, including the economic vintage actually known then;
`label_available_at` is when the target became settled. Targets must become
available after their prediction snapshot and before training starts.
Macro sources must be `observed`; Quant sources may be `observed` or `paper`.
Synthetic input is rejected. The 50-row code minimum is only an input floor,
not evidence that the history spans enough regimes or that a model is useful.

Training uses whole-snapshot chronological train/validation/test groups,
purges labels unavailable before the next evaluation boundary, fits early
stopping on validation only, and reports held-out metrics against training-only
baselines. Each role has its own process lock, session ID, dataset hash, metrics
and native JSON/checksummed ZIP artifact:

- `.runtime/models/council/macro_analyst.bundle.zip`
- `.runtime/models/council/quantitative_strategist.bundle.zip`

There is no trainable Risk Executive model. Paper-profit directional calibration
updates Quant reliability, never risk authority or macro structural-regime
labels. Existing legacy profile names are not silently renamed into new roles.

Artifacts remain advisory with `production_ready: false` and
`broker_execution_allowed: false`. Training a bundle does not activate it in
the running council: runtime Macro consumes explicit observed regime/bias
evidence; runtime Quant consumes the existing technical proposal/quality tools.
Separately trained predictions are available through `SpecialistModel.predict`
for evaluation; automatic model promotion and learned pair strategies are not
implemented by this change.

## Verification and activation status

Tests fit both model types on temporary fixtures, verify native reloads and
isolated CLI locking, and exercise vetoes, malformed approval bounds, stale
correlations, non-voting authority, paper training-off entry checks and private
entry containment. These fixtures are not actual market training sessions.

As of 2026-10-14, this change is source-ready and locally tested. No actual
macro/pair dataset has been supplied, no paid training job has been activated,
and no live order has been sent. Windows activation remains pending because
no Desktop Commander device is connected. The deployed website and Windows
runtime must not be presented as running these new specialists yet.

Primary references for the training contracts:

- [FRED/ALFRED real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html): use evidence from the economic vintage available at the decision time.
- [XGBoost sklearn estimator interface](https://xgboost.readthedocs.io/en/stable/python/sklearn_estimator.html): explicit validation data and early stopping.
- [scikit-learn time-series splits](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html): chronology matters for evaluation; this implementation additionally keeps simultaneous snapshots together and purges unavailable labels.
