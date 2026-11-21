# ATLAS Council documentation and activation

Reviewed on 21 October 2026. Current authority is the repository README and implemented PAPER path. Original source: https://github.com/imsamtaha/Trading-ai .

## Runtime and research are separate

The existing Windows monitor supports Council -> Senior Risk -> Executive -> PAPER -> settled-outcome journal -> bounded agent calibration. The demo launcher now enables that existing learning path by default. It still forces ATLAS_LIVE_TRADING=false and ATLAS_ENVIRONMENT=paper. Use -NoCouncilTraining to opt out. This setting applies when the launcher runs; committing it does not restart an already running worker.

The uploaded classifier is installed as atlas_training/train_agent.py. It runs offline walk-forward evaluation with a one-bar embargo and registers an MLflow challenger. --council-report emits atomic evidence for STC-04 (Quant Validator) and STC-09 (Evaluator). A registry champion alias never installs Council weights or an inference adapter. Features and models remain illustrative.

## Document register

| Document | Purpose | Authority |
| --- | --- | --- |
| ../../README.md | Current runtime and repository layout | Implemented architecture |
| ../ATLAS_STRUCTURE.md | Council and runtime boundaries | Current repository reference |
| ../ATLAS_DECISION_MATRIX.md | Deterministic decision rules | Repository reference |
| ../ATLAS_GIC_EVOLUTION_ENGINE.md | Evolution and evaluation design | Design and reference |
| ../ATLAS_NEWS_ROUTING.md | News routing and event context | Repository reference |
| ../ATLAS_VERIFIED_NEWS.md | Source validation and freshness | Repository reference |
| ../DEMO_OPERATIONS.md | Paper worker operations | Operations reference |
| ../../README_MT5.md | Windows terminal boundary | Operations reference |
| ../../ATLAS_LAUNCH.md | Launcher and installation | Operations reference |
| ../MT5_SUBMISSION_SAFETY.md | Broker isolation | Safety reference |
| ../GOOGLE_CLOUD_DEPLOY.md | Original application deployment | Deployment instructions only |
| ../GOOGLE_SIGN_IN.md | Authentication configuration | Deployment reference |
| sources/ATLAS_Realtime_Agent_Council_v2.1.md | Full realtime Council specification | Historical proposed design |
| sources/ATLAS_Council_v3_Edge_First.md | Expected value and cost-aware research | Historical proposed design |
| sources/ATLAS-Paper-Quality-Training-Plan-20261013.md | Dated PAPER evaluation and training plan | Historical evidence dated 13 October |

The v2.1 and v3 documents discuss live modes and alternative architectures. They are preserved without applying their proposed permissions. Their inclusion does not activate broker execution or prove their features are installed. Old deployment status and old performance reports are dated records, not current heartbeat evidence.

Original Drive references:

- Council folder: https://drive.google.com/drive/folders/1VOMVWQM2WsP0kzPO_X8KEiKQeG4E7QEd
- Training files: https://drive.google.com/drive/folders/1qxfQbligiXeN4f-vkvOoyIzC9d60sPuI
- Upgraded role register: https://docs.google.com/spreadsheets/d/1KIX8YWjwUIIqJzKRGzQzPnwaInVLm1NsoiL6YPR8vRA/edit
- Original Council register: https://docs.google.com/spreadsheets/d/1CqveHz9MJOAy6vdm5u3vn_sWgTHWK8gj86hXM-fDxCo/edit
- v2.1 source: https://drive.google.com/file/d/1s2sTirXMavRvZSTv6D8P-yf5l2KfqWb4/view
- v3 source: https://drive.google.com/file/d/1Am7ter5bZ2fOvcC3czApnh-Cndxbu9mz/view
- Training quality plan: https://drive.google.com/file/d/1POO3L5OlltvB6bRS0V-qyB0mVPpRk1QN/view
- Council overview PDF: https://drive.google.com/file/d/1WnLDXpIUbpoS6pkQAQYw1GU7Osmevj1u/view
- Earlier design: https://drive.google.com/file/d/1MmXxR-3qkgaBwQQqhHW5-PwGSVFEBsqE/view

## Training gates

Candidate OOS accuracy must exceed max(0.525, training-fold majority baseline OOS + 0.005), improve the existing champion by at least 0.005, have OOS/train stability >= 0.80, and confidence-bin ECE <= 0.10. Invalid or non-finite metrics reject promotion. The 0.525 floor is an illustrative classification gate; it is not a statistical significance or profitability test. Costs, spread, slippage, regimes and net expectancy require separate real strategy evaluation.

The former auto-promote upload is retained only as an original attachment, not installed as the active trainer. Current promotion requires --promote, all gates, and independent review. Default behavior leaves the champion unchanged.

## Windows PAPER activation

From the original project directory with the existing venv, .env and open MT5 DEMO terminal:

```powershell
.\scripts\start_atlas_demo.ps1
```

Inspect existing worker processes first and stop the old monitor before restarting; do not start a second copy against the same ledger. Keep risk and position limits unchanged. Confirm current heartbeat, unique newly settled examples in data/atlas_council_training.jsonl, and refreshed data/atlas_council_profile.json. No Windows process has been started by this repository change.

## Android and Ubuntu PAPER Council

Build an offline zipapp from a checked-out GitHub revision, using Python 3.10 or newer:

```sh
python scripts/build_atlas_mobile_council.py --output ATLAS_Paper_Council.pyz
```

Download the archive to Android and use Termux with Python installed. If necessary,
run `termux-setup-storage` and grant access to Downloads.

```sh
python ~/storage/downloads/ATLAS_Paper_Council.pyz
python ~/storage/downloads/ATLAS_Paper_Council.pyz --journal ~/storage/downloads/atlas_council_training.jsonl
```

On Ubuntu, run the same commands with your actual download path. The first
command runs a synthetic self-test. The second reads a local copy of the settled
PAPER journal and prints a calibration profile. Identical duplicate snapshots
count once, and conflicting records or missing explicit PAPER markers stop
the run. On Windows, the default journal path relative to the worker checkout
is `data/atlas_council_training.jsonl`. Keep the copied journal private.

The archive contains the Council, risk-to-Executive adapter, Executive and
training modules and the nine-seat contract library. Its command-line interface
runs offline calibration. It requires only Python and leaves the Windows MT5
worker independent.

## Offline MLflow research

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-training.txt
.\.venv\Scripts\python.exe -m atlas_training.train_agent --agent trend --csv data/XAUUSD_M15.csv --mlflow-uri http://127.0.0.1:5000 --council-report data/council_training_review.json
```

Use actual ordered OHLC history on the worker. Do not label generated candles as MT5 history. The local validation used generated candles solely to test the pipeline. MLflow 3.17.2 is pinned to the tested release; the model is stored with skops and only the in-process fitted sklearn.tree._tree.Tree type is explicitly trusted. Reference: https://mlflow.org/docs/latest/ml/model-registry/tutorial .

## Validation

```sh
python -m pytest -q tests/test_training_harness.py tests/test_training_harness_safety.py tests/test_atlas_council_training.py tests/test_atlas_council_adapters.py tests/test_atlas_executive_paper_architecture.py
```

42 focused tests passed locally. A complete SQLite-backed MLflow run registered challenger v1 and v2 on repeat runs and rejected the synthetic candidate: OOS 0.5368, majority baseline about 0.5737, train 1.0, stability 0.5368, ECE 0.2681. Champion was not created. These numbers are synthetic test output, not ATLAS performance.

## Connected services and remaining verification

Bigdata.com can supply advisory research through the connected ChatGPT tools. No unattended provider credential or server adapter has been established by this change. Preserve source timestamps and UNAVAILABLE status when inputs are absent. Do not turn market research into broker orders.

Sites lists an older private dashboard prototype with no custom domain attached. The original justai-atlas.online/sam deployment source remains unresolved. This change does not publish over that domain or replace it with the older prototype. Production worker heartbeat, Windows execution, live MLflow endpoint and original website deployment still require verification on the original host.
