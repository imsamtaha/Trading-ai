"""Read-only, fail-closed status for the ATLAS Paper Council calibration profile.

Never exposes raw opinions, snapshots, broker credentials, or file-system paths.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from math import isfinite
from pathlib import Path
from typing import Any


def _invalid_number(value: str) -> None:
    raise ValueError(f"Non-finite JSON value: {value}")


def _count(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("Invalid nonnegative integer")
    return value


def read_shadow_summary(
    *, path: str | Path | None = None, now: datetime | None = None
) -> dict[str, Any]:
    """Return a minimal, non-sensitive training readout. Missing/invalid is not success."""
    base: dict[str, Any] = {
        "status": "MISSING",
        "source": "ATLAS_COUNCIL_PROFILE",
        "training_environment": "PAPER",
        "broker_execution_allowed": False,
        "automatic_live_activation": False,
        "last_training_at": None,
        "settled_paper_examples": None,
        "agents_observed": None,
        "agents_calibrated": None,
        "agents_at_baseline": None,
        "freshness_limit_hours": 24,
    }
    source = Path(path) if path is not None else Path(
        os.getenv("ATLAS_COUNCIL_PROFILE", "data/atlas_council_profile.json")
    )
    try:
        if not source.exists():
            return base
        profile = json.loads(source.read_text(encoding="utf-8"), parse_constant=_invalid_number)
        if not isinstance(profile, dict):
            raise ValueError("Profile must be an object")
        if profile.get("training_environment") != "PAPER":
            raise ValueError("Council profile must be PAPER-only")
        if profile.get("broker_execution_allowed") is not False:
            raise ValueError("Council profile must prohibit broker execution")
        total = _count(profile.get("total_examples"))
        minimum = _count(profile.get("minimum_samples"))
        if minimum < 1:
            raise ValueError("Minimum samples must be positive")
        agents = profile.get("agents")
        if not isinstance(agents, dict):
            raise ValueError("Invalid agent summary")
        calibrated = 0
        baseline = 0
        for name, stats in agents.items():
            if not isinstance(name, str) or not name or not isinstance(stats, dict):
                raise ValueError("Invalid agent")
            samples = _count(stats.get("samples"))
            if samples > total:
                raise ValueError("Agent sample count exceeds settled Paper examples")
            weight = float(stats.get("weight"))
            if not isfinite(weight) or not 0.5 <= weight <= 1.5:
                raise ValueError("Invalid bounded reliability weight")
            locked = stats.get("locked_baseline")
            if not isinstance(locked, bool) or locked != (samples < minimum):
                raise ValueError("Invalid baseline lock")
            if locked:
                if weight != 1.0:
                    raise ValueError("Baseline agent must retain neutral weight")
                baseline += 1
            else:
                calibrated += 1
        raw_timestamp = profile.get("generated_at")
        if not isinstance(raw_timestamp, str):
            raise ValueError("Missing generation timestamp")
        timestamp = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            raise ValueError("Generation timestamp must have a timezone")
        timestamp = timestamp.astimezone(timezone.utc)
        clock = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        if timestamp > clock + timedelta(minutes=5):
            raise ValueError("Profile timestamp is in the future")
        status = "FRESH" if clock - timestamp <= timedelta(hours=24) else "STALE"
        return {
            **base,
            "status": status,
            "last_training_at": timestamp.isoformat(),
            "settled_paper_examples": total,
            "agents_observed": len(agents),
            "agents_calibrated": calibrated,
            "agents_at_baseline": baseline,
        }
    except (OSError, ValueError, TypeError, OverflowError):
        return {**base, "status": "INVALID"}
