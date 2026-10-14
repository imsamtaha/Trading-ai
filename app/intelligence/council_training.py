from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
from typing import Any, Iterable, Mapping


VALID_OUTCOMES = {"BUY", "SELL", "HOLD"}


def _score(value: Any, *, field: str) -> float:
    score = float(value)
    if not isfinite(score) or not 0.0 <= score <= 1.0:
        raise ValueError(f"{field} must be a finite value between 0 and 1")
    return score


def _reject_constant(value: str) -> None:
    raise ValueError(f"Invalid JSON numeric constant: {value}")


@dataclass(frozen=True)
class PaperTrainingExample:
    snapshot_id: str
    realized_direction: str
    opinions: tuple[dict[str, Any], ...]
    execution_environment: str = "PAPER"
    broker_execution_allowed: bool = False

    def __post_init__(self) -> None:
        snapshot_id = self.snapshot_id.strip()
        realized = self.realized_direction.upper()
        environment = self.execution_environment.upper()
        if not snapshot_id:
            raise ValueError("snapshot_id must not be empty")
        if realized not in VALID_OUTCOMES:
            raise ValueError("realized_direction must be BUY, SELL, or HOLD")
        if environment != "PAPER":
            raise ValueError("ATLAS Council training accepts PAPER outcomes only")
        if self.broker_execution_allowed:
            raise ValueError("Broker-executed outcomes cannot train the Paper Council")
        object.__setattr__(self, "snapshot_id", snapshot_id)
        object.__setattr__(self, "realized_direction", realized)
        object.__setattr__(self, "execution_environment", environment)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PaperTrainingExample":
        opinions = payload.get("opinions") or ()
        if not isinstance(opinions, (list, tuple)):
            raise ValueError("opinions must be a list")
        return cls(
            snapshot_id=str(payload.get("snapshot_id", "")),
            realized_direction=str(payload.get("realized_direction", "")),
            opinions=tuple(dict(item) for item in opinions if isinstance(item, Mapping)),
            execution_environment=str(payload.get("execution_environment", "PAPER")),
            broker_execution_allowed=bool(payload.get("broker_execution_allowed", False)),
        )


class AtlasCouncilTrainer:
    """Calibrates agent reliability from settled Paper outcomes only."""

    def __init__(
        self,
        *,
        minimum_samples: int = 5,
        min_weight: float = 0.5,
        max_weight: float = 1.5,
    ) -> None:
        if minimum_samples < 1:
            raise ValueError("minimum_samples must be at least 1")
        self.minimum_samples = minimum_samples
        self.min_weight = float(min_weight)
        self.max_weight = float(max_weight)

    def fit(self, examples: Iterable[PaperTrainingExample]) -> dict[str, Any]:
        stats: dict[str, dict[str, float]] = {}
        total_examples = 0

        for example in examples:
            total_examples += 1
            for opinion in example.opinions:
                agent = str(opinion.get("agent", "")).strip()
                if agent in {"risk_executive", "recovery_guardian", "macro_analyst"}:
                    # Risk is deterministic; structural regimes need their own
                    # labels, not the direction of a settled paper trade.
                    continue
                decision = str(opinion.get("decision", "")).upper()
                if not agent or decision not in VALID_OUTCOMES:
                    continue
                confidence = _score(opinion.get("confidence", 0.0), field="confidence")
                correct = 1.0 if decision == example.realized_direction else 0.0
                row = stats.setdefault(agent, {"samples": 0.0, "correct": 0.0, "brier_sum": 0.0})
                row["samples"] += 1.0
                row["correct"] += correct
                row["brier_sum"] += (confidence - correct) ** 2

        agents: dict[str, dict[str, Any]] = {}
        for agent, row in sorted(stats.items()):
            samples = int(row["samples"])
            correct = int(row["correct"])
            posterior_accuracy = (correct + 1.0) / (samples + 2.0)
            brier_score = row["brier_sum"] / samples if samples else 1.0
            calibration_quality = max(0.0, min(1.0, 1.0 - brier_score))
            reliability = (0.7 * posterior_accuracy) + (0.3 * calibration_quality)
            locked = samples < self.minimum_samples
            weight = 1.0 if locked else max(self.min_weight, min(self.max_weight, 0.5 + reliability))
            agents[agent] = {
                "samples": samples,
                "correct": correct,
                "posterior_accuracy": round(posterior_accuracy, 4),
                "brier_score": round(brier_score, 4),
                "weight": round(weight, 4),
                "locked_baseline": locked,
            }

        return {
            "version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "training_environment": "PAPER",
            "broker_execution_allowed": False,
            "minimum_samples": self.minimum_samples,
            "total_examples": total_examples,
            "agents": agents,
        }


def agent_weight(profile: Mapping[str, Any] | None, agent: str) -> float:
    if agent in {"risk_executive", "recovery_guardian"}:
        return 1.0
    if not profile:
        return 1.0
    agents = profile.get("agents")
    if not isinstance(agents, Mapping):
        return 1.0
    row = agents.get(agent)
    if not isinstance(row, Mapping):
        return 1.0
    try:
        weight = float(row.get("weight", 1.0))
    except (TypeError, ValueError):
        return 1.0
    if not isfinite(weight) or not 0.5 <= weight <= 1.5:
        return 1.0
    return weight


class CouncilTrainingJournal:
    """Append-only settled Paper examples used for offline/replay calibration."""

    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path or os.getenv("ATLAS_COUNCIL_TRAINING_JOURNAL", "data/atlas_council_training.jsonl"))

    def append(self, example: PaperTrainingExample) -> dict[str, Any]:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "snapshot_id": example.snapshot_id,
            "realized_direction": example.realized_direction,
            "opinions": list(example.opinions),
            "execution_environment": "PAPER",
            "broker_execution_allowed": False,
        }
        encoded = json.dumps(payload, allow_nan=False, separators=(",", ":")) + "\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        return payload

    def load(self) -> list[PaperTrainingExample]:
        if not self.path.exists():
            return []
        examples: list[PaperTrainingExample] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line, parse_constant=_reject_constant)
                    examples.append(PaperTrainingExample.from_dict(payload))
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    raise ValueError(f"Invalid council training record at line {line_number}") from exc
        return examples


def save_profile(profile: Mapping[str, Any], path: str | None = None) -> Path:
    target = Path(path or os.getenv("ATLAS_COUNCIL_PROFILE", "data/atlas_council_profile.json"))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(dict(profile), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return target
