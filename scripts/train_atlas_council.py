from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.intelligence.council_training import (
    AtlasCouncilTrainer,
    CouncilTrainingJournal,
    save_profile,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Train ATLAS Council weights from settled Paper outcomes.")
    parser.add_argument("--journal", default="data/atlas_council_training.jsonl")
    parser.add_argument("--output", default="data/atlas_council_profile.json")
    parser.add_argument("--minimum-samples", type=int, default=5)
    parser.add_argument("--observed-ledger", help="Cross-check original predictions and settled MT5 quote evidence; train chronological calibration.")
    args = parser.parse_args()

    if Path(args.output).resolve() in {Path(args.journal).resolve(), Path(args.observed_ledger).resolve() if args.observed_ledger else None}:
        parser.error("Output must not overwrite a training source")
    if args.observed_ledger:
        from app.intelligence.council_calibration import train_observed
        profile = train_observed(args.journal, args.observed_ledger)
    else:
        journal = CouncilTrainingJournal(args.journal)
        examples = journal.load()
        trainer = AtlasCouncilTrainer(minimum_samples=args.minimum_samples)
        profile = trainer.fit(examples)
    target = save_profile(profile, args.output)

    print(
        json.dumps(
            {
                "status": "OK",
                "training_environment": "PAPER",
                "broker_execution_allowed": False,
                "examples": profile["total_examples"],
                "agents": len(profile["agents"]),
                "profile_version": profile["version"],
                "accepted_agents": profile.get("accepted_agents", []),
                "validation": "chronological_quote_backed" if args.observed_ledger else "legacy_in_sample_only",
                "profile": str(target),
            },
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
