from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.intelligence.council_training import (
    AtlasCouncilTrainer,
    CouncilTrainingJournal,
    merge_training_examples,
    save_profile,
)
from app.intelligence.paper_memory import paper_setups, read_paper_archive


def main() -> int:
    parser = argparse.ArgumentParser(description="Train ATLAS Council weights from settled Paper outcomes.")
    parser.add_argument("--journal", default="data/atlas_council_training.jsonl")
    parser.add_argument("--history-ledger", type=Path, help="Archived private ATLAS PAPER ledger JSON")
    parser.add_argument("--output", default="data/atlas_council_profile.json")
    parser.add_argument("--minimum-samples", type=int, default=5)
    args = parser.parse_args()

    try:
        journal = CouncilTrainingJournal(args.journal)
        archive = paper_setups(
            read_paper_archive(args.history_ledger), before=datetime.now(timezone.utc),
        )
        examples = merge_training_examples(journal.load(), (setup.example for setup in archive))
        if not examples:
            raise ValueError("No settled PAPER examples with Council provenance")
        trainer = AtlasCouncilTrainer(minimum_samples=args.minimum_samples)
        profile = trainer.fit(examples)
        target = save_profile(profile, args.output)
    except (OSError, TypeError, ValueError) as exc:
        parser.error(str(exc))

    print(
        json.dumps(
            {
                "status": "OK",
                "training_environment": "PAPER",
                "broker_execution_allowed": False,
                "examples": profile["total_examples"],
                "agents": len(profile["agents"]),
                "profile": str(target),
            },
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
