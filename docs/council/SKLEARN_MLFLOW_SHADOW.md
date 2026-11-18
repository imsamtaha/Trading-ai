# ATLAS | Scikit-learn and MLflow PAPER research

## Scope

This is an **offline-only, read-only model evaluation pipeline**. It evaluates each agent's scores independently using settled PAPER Council outcomes and logs inspectable evidence to a local MLflow tracking server. It **does not** turn on broker execution, change MT5 permissions, promote model registry champions, or write active Council weights.

The default governance outcome remains **HOLD_BASELINE**. An eligible score produces a *candidate weight for human review*, not an active weight.

## Per-agent scoring rules

- Only `execution_environment=PAPER` and `broker_execution_allowed=false` are accepted. Duplicate snapshot IDs, invalid decisions, or invalid confidence fail closed.
- Evaluate each agent independently with `LogisticRegression`; inputs are that agent's confidence and decision category, and the target is correctness against the **settled** PAPER outcome.
- **At least 80** settled samples per agent; train on the earlier 75%, exclude one snapshot as an embargo, evaluate on the later 25% with at least 20 held-out observations; no shuffle.
- Require OOS accuracy >= max(0.525, chronological majority baseline OOS accuracy + 0.005); stability >= 0.80; calibration ECE <= 0.10; Brier score improvement >= 0.01 over the train-prevalence baseline.
- Any PAPER source file older than **48 hours** or future-dated is ineligible for candidate weights (stale-data veto). A passing proposal must be reviewed by STC-04, STC-09, and Senior Risk before any future, separately approved PAPER-only adoption.
- Every result has a source SHA-256, timestamp, sample count, individual gate reasons, and read-only status. The API never imports broker packages and the CLI has no promote flag.

## Local MLflow (Windows, private only)

Keep tracking on `http://127.0.0.1:5000` bound to localhost, not a public domain. Use a dedicated Python virtual environment outside the production repository. The local SQLite database and artifacts must remain in the private research folder and outside Git.

```powershell
$root = Join-Path $env:LOCALAPPDATA 'ATLAS\research-mlflow'
$python = Join-Path $root 'venv\Scripts\python.exe'
$src = Join-Path $root 'training-src'
$journal = Join-Path $HOME 'ATLAS\.runtime\paper\atlas_council_training.jsonl'
$report = Join-Path $root 'evidence\council-agent-scores.json'
Set-Location $src
& $python -m atlas_training.council_sklearn_research --journal $journal --report $report --mlflow-uri 'http://127.0.0.1:5000'
```

If the journal is missing, malformed, stale, or insufficient, the evaluation holds baseline. If the MLflow server cannot be reached, the command must fail rather than claim it logged evidence.

Offline OHLC smoke/evaluation (does not require MLflow):

```bash
python -m atlas_training.sklearn_shadow --check
python -m atlas_training.sklearn_shadow --agent STC-04 --csv path/to/actual-OHLC.csv --report research/ohlc-review.json
```

The OHLC feature and target are illustrative, not production signals. Simulated test data must never be labeled verified market performance.

## Focused validation

```bash
python -m pytest -q tests/test_council_sklearn_research.py tests/test_sklearn_shadow.py tests/test_training_harness.py tests/test_training_harness_safety.py
```

**Release gate:** passing tests + current genuine settled PAPER ledger + calibrated out-of-sample metrics + separate Senior Risk and Governance review. Until that evidence exists, active Council weights and broker execution remain unchanged.
