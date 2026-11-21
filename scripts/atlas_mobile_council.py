"""Inspect settled PAPER Council outcomes on a phone with Python."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.intelligence.council_training import AtlasCouncilTrainer, PaperTrainingExample
from app.intelligence.nine_seat_council import classify_instrument


def reject_nonfinite(value: str) -> None:
    raise ValueError(f"Unexpected JSON constant {value}")


def read_examples(path: Path) -> list[PaperTrainingExample]:
    examples: dict[str, PaperTrainingExample] = {}
    with path.open(encoding="utf-8-sig") as journal:
        for number, line in enumerate(journal, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line, parse_constant=reject_nonfinite)
                if (
                    not isinstance(row, dict)
                    or row.get("execution_environment") != "PAPER"
                    or row.get("broker_execution_allowed") is not False
                ):
                    raise ValueError("missing explicit PAPER provenance")
                example = PaperTrainingExample.from_dict(row)
                if example.snapshot_id in examples and examples[example.snapshot_id] != example:
                    raise ValueError("conflicting records for one snapshot")
                examples[example.snapshot_id] = example
            except (TypeError, ValueError) as error:
                raise ValueError(f"Journal line {number}: {error}") from error
    if not examples:
        raise ValueError("Journal contains no settled PAPER examples.")
    return list(examples.values())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", type=Path, help="Local copy of settled PAPER Council JSONL")
    args = parser.parse_args()
    trainer = AtlasCouncilTrainer()

    if args.journal is None:
        example = PaperTrainingExample(
            snapshot_id="mobile-self-test",
            realized_direction="BUY",
            opinions=({"agent": "technical", "decision": "BUY", "confidence": 0.7},),
        )
        profile = trainer.fit([example])
        if (
            classify_instrument("XAUUSD") != "gold"
            or profile["total_examples"] != 1
            or profile["broker_execution_allowed"] is not False
            or profile["agents"]["technical"]["weight"] != 1.0
        ):
            raise RuntimeError("ATLAS PAPER Council self-test failed.")
        print("ATLAS PAPER Council self-test passed (1 synthetic example).")
        return 0

    try:
        profile = trainer.fit(read_examples(args.journal))
    except (OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(profile, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
