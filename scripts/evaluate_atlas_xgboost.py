"""Read-only offline Council reliability research from settled Paper journal."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.intelligence.council_training import CouncilTrainingJournal
from app.intelligence.xgboost_experiment import evaluate_paper_examples


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline XGBoost research on settled Paper Council opinions")
    parser.add_argument("--journal", default="data/atlas_council_training.jsonl")
    parser.add_argument("--output", default=None, help="Optional report JSON path, not a training profile")
    args = parser.parse_args()
    try:
        report = evaluate_paper_examples(CouncilTrainingJournal(args.journal).load())
    except (ValueError, RuntimeError, OSError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc), "broker_execution_allowed": False}))
        return 2
    if args.output:
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
