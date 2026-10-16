# ATLAS XGBoost: offline Council opinion evaluation

**Status:** optional research tool. **No trading execution, model promotion, Council weighting changes, or deployment.**

## Source / scope

- Project discussion: https://chatgpt.com/s/t_6ad18619ebac8191a042644f782f0aa6
- Full shared-chat content was not accessible at review time. The discussion included a sales/CSAT XGBoost sample; that commercial prototype must not be treated as a verified trading model.
- Production Council weighting continues to use `app/intelligence/council_training.py`.
- This independent experiment only estimates whether historical Council agent opinions agreed with **settled PAPER labels**. A trade outcome label is a proxy and is not a calibrated probability of profit.

## Inputs and guardrails

- The existing append-only `data/atlas_council_training.jsonl` created by Council training, oldest first.
- Every sample must be PAPER, not broker-executed, with unique snapshot ID and well-formed, unique Council agent opinions.
- Strict chronological split by snapshot group; holdout snapshots never participate in fitting the one-hot encoder or classifier.
- Minimum 20 training snapshots and 10 test snapshots; both partitions must contain correct and incorrect opinion labels. These are **minimum technical checks**, not statistical proof or a readiness threshold.
- XGBoost is optional and is not loaded by the server/monitor. There is no persisted ML model, no automatic confidence adjustment, no changed Council weights, and no broker connection.
- Reports compare Brier score and log loss against a train-prevalence-only baseline, plus held-out ROC AUC. Lower Brier and log loss is better. The "observational improvement" flag is not approval for trading.
- Repeated snapshots are rejected instead of silently inflating sample sizes. Journal append order must reflect settlement chronology.

## Run offline

```bash
python -m pip install -r requirements-ml.txt
python scripts/evaluate_atlas_xgboost.py --journal data/atlas_council_training.jsonl --output data/atlas_xgboost_report.json
python -m pytest -q tests/test_atlas_xgboost_experiment.py
```

The `data/` directory is excluded from Git. `BLOCKED` output means missing or invalid evidence; it is not a successful evaluation. The script never touches `atlas_council_profile.json`.

## Before using results in decisions

Require an independent review of data provenance, labels, coverage across assets/regimes, grouped walk-forward evaluation, leakage tests, class imbalance, and reliability/calibration curves. Validate on substantially more distinct settled Paper outcomes and establish governance before considering any integration. Senior Risk, Executive HOLD checks, and broker isolation remain authoritative. Synthetic outcomes must never be described as market performance.
