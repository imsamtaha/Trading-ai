#!/usr/bin/env bash
# ATLAS: manual PAPER-only Council training session for Linux/AWS CloudShell.
# Usage: bash scripts/atlas_paper_cloudshell_session.sh [--check|--train]
# Never starts a broker, trading worker, or network listener.
set -euo pipefail
umask 077

mode="${1:---check}"
case "$mode" in
  --check|--train) ;;
  *) echo "Usage: bash scripts/atlas_paper_cloudshell_session.sh [--check|--train]" >&2; exit 2 ;;
esac
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

# Guard flags are explicit and override any unsafe inherited shell values.
export ATLAS_LIVE_TRADING=false
export ATLAS_ENVIRONMENT=paper
export ATLAS_DASHBOARD_ONLY=true
export ATLAS_AGENT_PAPER_EXECUTION_ENABLED=false
export ATLAS_COUNCIL_TRAINING_ENABLED=true

journal="${ATLAS_COUNCIL_TRAINING_JOURNAL:-$root/data/atlas_council_training.jsonl}"
output="${ATLAS_COUNCIL_PROFILE:-$root/data/atlas_council_profile.json}"
if [[ ! -s "$journal" ]]; then
  echo "NOT READY: missing or empty settled PAPER Council journal: $journal" >&2
  echo "No training was started. Use a genuine atlas_council_training.jsonl with settled PAPER Council opinions." >&2
  exit 4
fi

python3 - "$journal" <<'PY'
import sys
from app.intelligence.council_training import CouncilTrainingJournal

samples = CouncilTrainingJournal(sys.argv[1]).load()
if not samples:
    raise SystemExit("NOT READY: journal contains no PAPER Council examples")
opinions = sum(len(sample.opinions) for sample in samples)
if opinions == 0:
    raise SystemExit("NOT READY: examples contain no Council opinions")
print(f"ATLAS PAPER journal validated: {len(samples)} settled examples, {opinions} agent opinions")
PY

if [[ "$mode" == "--check" ]]; then
  echo "READY FOR MANUAL TRAINING; broker execution disabled; no files changed."
  exit 0
fi

python3 scripts/train_atlas_council.py \
  --journal "$journal" \
  --output "$output" \
  --minimum-samples 5

python3 - "$output" <<'PY'
import json
import sys
from pathlib import Path
profile = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if profile.get("training_environment") != "PAPER" or profile.get("broker_execution_allowed") is not False:
    raise SystemExit("SAFETY CHECK FAILED: profile is not PAPER-only")
print(f"TRAINING COMPLETED: {profile['total_examples']} settled examples; PAPER-only profile verified")
PY
