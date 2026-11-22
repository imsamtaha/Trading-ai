# Council safety and observed PAPER training

The thresholds committed in `b6b847e` now have a corresponding policy evaluator in
`src/council/consensus_aggregator.py`. The evaluator validates risk numbers, enforces
CVaR, prevents callers from relaxing configured limits, rejects duplicate voters,
and requires admitted agents from at least two active roles. Admission checks the
configured validation/demo/demotion metrics. Missing admission evidence returns HOLD.

All outputs retain `execute=false`, `broker_execution_allowed=false`, and
`lot_size=0`. A valid recommendation has `final_action` and a separate
`suggested_paper_lot_size`. The module has no broker execution channel. The new
3% CVaR limit is an explicit PAPER policy default, not a fitted or market-validated
risk recommendation. Existing role thresholds are preserved. Operators must validate
policies for their own instruments before any future execution integration.

Admission records are trusted server configuration supplied to the evaluator; votes
cannot grant themselves admission by sending `LIVE_EXECUTION`. The three configured
roles are MOMENTUM, MEAN_REVERSION and NEWS_SENTIMENT. The existing app's agent names
are separate identities: training does not silently relabel `technical`, `confidence`
or `quantitative_strategist` as those roles, or invent missing role history.

The existing `AtlasCouncilCoordinator` also rejects duplicate identities and reads
accepted version-2 calibration profiles. Risk and recovery vetoes remain unlearned;
macro regime classification is excluded from directional confidence training.

From a checked-out repository, run the Windows validation entry point:

```powershell
.\ATLAS_COUNCIL_INSTALL.ps1 -Python 'C:\path\to\python.exe'
```

It verifies its repository root, validates the policy and runs the safety tests.
It writes no source files, installs no dependencies, and performs no Git mutation.
Provide a Python environment with pytest installed. Every native command's exit
code is checked before reporting success. GitHub Actions runs mandatory council
tests plus the existing full suite, and separately tests Windows failure handling.

Train on snapshots of the actual journal and settled paper ledger:

```powershell
python scripts/train_atlas_council.py `
  --journal 'data\observed-source\journal.jsonl' `
  --observed-ledger 'data\observed-source\ledger.json' `
  --output 'data\council-observed-profile.json'
```

The inputs are read-only. Do not commit private journals, ledgers or account data.
The generated profile records source hashes, exclusions, partition sizes and scores.
This is offline training: it does not start MT5, place demo orders, or switch a running
service's model. To evaluate the artifact in the updated app, load the JSON profile
and pass it as `agent_profile` to `AtlasCouncilCoordinator.build_package`.

Records must match their original entry prediction and settled ledger label, carry
explicit PAPER/no-broker provenance, and include MT5 entry and exit quotes. The
recorded broker clock offset is used to check both quote timestamps within 60 seconds
of their events. Missing/stale quotes are excluded. Duplicate identities, altered
labels, invalid numeric values, and inconsistent timestamps abort the run.

`INCOMPLETE_EVIDENCE` quality flags are counted in the report. They do not exclude
confidence-calibration rows that satisfy every required prediction/label/quote check;
the calibrator does not use the missing technical indicators as features. These
records are observed-market PAPER simulations. They do not prove broker fills or
the historical account type; a current demo terminal check cannot prove those facts.

Each observed agent gets an independent monotonic logistic confidence calibrator.
Whole prediction-time groups are split approximately 60/20/20. Training labels must
be available before validation begins; validation labels must be available before
the holdout begins. Overlapping rows are purged. At least 20 training rows, 10
validation rows and 10 holdout rows are required, with both outcome classes in train.
Regularization is chosen using validation only. An artifact is accepted for PAPER
inference only if Brier score improves by at least 0.005 against both raw confidence
and the training-prior baseline on validation and the untouched holdout.

The holdout is a one-time acceptance check. Do not tune parameters against its result
or repeatedly promote using the same historical slice; collect new settled data for
the next evaluation. A rejected candidate is retained for inspection and inference
falls back to raw confidence. `accepted_agents=[]` is a valid completed evaluation,
not proof that a new model was activated. Without `--observed-ledger`, the older
trainer remains available and is explicitly reported as `legacy_in_sample_only`.
