# ATLAS Training Accelerator (Offline Replay v1)

## Purpose

Fast, reproducible **PAPER-only** experiments to calibrate council confidence weights without changing operational ATLAS profile, monitor, execution policy, or broker permissions. This tool uses the existing settled paper-training journal. Replaying 76 examples **does not create 76 new independent market observations**.

## Usage (Windows, from ATLAS folder)

```powershell
node scripts/atlas_training_accelerator.mjs
node --test tests/test_training_accelerator.mjs
```

Optional switches: `--journal <path>`, `--output-dir <research-path>`, `--min-improvement 0.01`.

Default input: `.runtime/paper/atlas_council_training.jsonl` (read-only).
Default output: `.runtime/research/training-accelerator/latest-report.json`.

## Safeguards

- Rejects missing/wrong timestamps, non-PAPER or broker-enabled examples, invalid numeric confidence and conflicting labels for the same snapshot.
- Removes exact duplicated snapshots before computing sample counts.
- Uses chronological **60% train / 20% validation / 20% untouched test**. Minimum 30 settled unique samples required.
- Computes a baseline from the existing trainer's reliability formula, then trials **bounded weights from 0.50 to 1.50** to minimize Brier score on training only.
- Shadow-accepts a candidate only when validation Brier improves by at least 0.01 and there are at least 6 validation samples for the agent. Otherwise keeps the training-derived baseline in the shadow report.
- Reports out-of-sample Brier, directional accuracy, disagreement rate and highest-confidence historical mistakes.
- **NO** edits to operational `atlas_council_profile.json`, journal or trading settings. Never executes orders, connects to MT5, or enables live trading.
- No online promotion is built. "SHADOW_ACCEPTED" refers only to a hypothetical calibration candidate in the research report.

## Initial 2026-10-08 replay, 76 examples

All 76 settled examples contain unanimous decisions from the two trained agents (technical + confidence). Thus changing their weights does not independently create a better direction signal.

- Technical: validation Brier improved from 0.34036 to 0.28046 with candidate weight 0.50; shadow-accepted only. Untouched test Brier improved from 0.38324 to 0.20953.
- Confidence: candidate 0.50 worsened validation Brier from 0.26780 to 0.31266; shadow-rejected.
- Production PAPER profile remains unchanged. The shadow baselines trained on the older 60% segment are not the latest runtime profile weights; do not confuse them.

## Limits, next version

The current training labels come only from settled positions. They do **not** establish the counterfactual outcomes of rejected trades; sample selection bias, intraday changes and non-independent agent opinions are material concerns. Replay speed is not the same thing as training throughput or directional improvement. Next priority is **independent** signals (regime, news, macro, or price-action abstention) with timestamped ex-ante predictions, blocked walk-forward validation across days/symbols, and a minimum independent sample requirement before any runtime experiment.

## Windows environment warning observed 2026-10-08

The existing `.venv/Scripts/python.exe --version` failed with code 103, reporting a missing Python 3.13 base path. The running paper monitor may continue while already loaded, but a restart may fail. This Node tool works independently. Repair the Python installation / venv only through a separately verified maintenance workflow; do not change the paper runtime to make this research tool work.
