"""Contextual sizing evidence from settled trades with PAPER Council provenance."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import isfinite
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Mapping

from app.intelligence.council_adapters import settled_paper_example
from app.intelligence.council_training import PaperTrainingExample


def _utc(value: str) -> datetime:
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("A PAPER timestamp requires a timezone")
    return stamp.astimezone(timezone.utc)


@dataclass(frozen=True)
class SettledPaperSetup:
    key: tuple[str, str, str, str]
    opened: datetime
    closed: datetime
    realized_r: float
    example: PaperTrainingExample

    @classmethod
    def from_trade(cls, trade: Mapping[str, Any]) -> SettledPaperSetup:
        if trade.get("status") != "CLOSED":
            raise ValueError("Expected a settled PAPER trade")
        if (
            trade.get("broker_execution_allowed", False) is not False
            or trade.get("execution_environment", "PAPER") != "PAPER"
        ):
            raise ValueError("Expected a PAPER ledger record")

        symbol, strategy, timeframe, direction = (
            trade[field].strip().upper() for field in ("symbol", "strategy", "timeframe", "direction")
        )
        action = {"LONG": "BUY", "SHORT": "SELL"}[direction]
        if not all((symbol, strategy, timeframe)):
            raise ValueError("Incomplete PAPER setup")
        opened, closed = _utc(trade["opened_at"]), _utc(trade["closed_at"])
        realized_r = trade["r_multiple"]
        if (
            closed <= opened or isinstance(realized_r, bool)
            or not isinstance(realized_r, (int, float)) or not isfinite(realized_r)
        ):
            raise ValueError("Invalid PAPER settlement")

        context = trade["training_context"]
        council, intent = context["council"], context["trade_intent"]
        if (
            council.get("symbol") != symbol or intent.get("symbol") != symbol
            or intent.get("decision") != action
            or council["senior_risk_management"]["assessment"] != "RISK_ACCEPTABLE"
        ):
            raise ValueError("Council approval does not match the settled PAPER trade")
        opposite = "SELL" if action == "BUY" else "BUY"
        example = settled_paper_example(
            council=council, trade_intent=intent,
            realized_direction=action if realized_r > 0 else opposite if realized_r < 0 else "HOLD",
        )
        if not example.opinions:
            raise ValueError("Missing PAPER Council opinions")
        return cls((symbol, strategy, timeframe, direction), opened, closed, realized_r, example)


def paper_setups(trades: Iterable[Mapping[str, Any]], *, before: datetime) -> list[SettledPaperSetup]:
    setups: dict[str, SettledPaperSetup] = {}
    for trade in trades:
        try:
            setup = SettledPaperSetup.from_trade(trade)
        except (AttributeError, KeyError, OverflowError, TypeError, ValueError):
            continue
        if setup.closed >= before:
            continue
        previous = setups.setdefault(setup.example.snapshot_id, setup)
        if previous != setup:
            raise ValueError("Conflicting PAPER ledger records for one Council snapshot")
    return list(setups.values())


def read_paper_archive(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    archive = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(archive, dict) or not isinstance(archive.get("closed_trades"), list):
        raise ValueError("Expected an ATLAS PAPER ledger export with closed_trades")
    return archive["closed_trades"]


def sizing_evidence(
    setups: Iterable[SettledPaperSetup],
    *,
    key: tuple[str, str, str, str],
    before: datetime,
) -> dict[str, Any] | None:
    """Require a chronological holdout and positive results under a cost stress."""
    cutoff = before - timedelta(days=180)
    matches = sorted(
        (setup for setup in setups if setup.key == key and cutoff <= setup.closed < before),
        key=lambda setup: (setup.opened, setup.example.snapshot_id),
    )[-80:]
    if len(matches) < 24 or len({setup.opened.date() for setup in matches}) < 5:
        return None
    holdout_size = max(8, len(matches) // 3)
    holdout = matches[-holdout_size:]
    earlier = [setup for setup in matches[:-holdout_size] if setup.closed < holdout[0].opened]
    if len(earlier) < 16 or len({setup.opened.date() for setup in holdout}) < 2:
        return None

    def stressed_mean(group: list[SettledPaperSetup]) -> float:
        # Cap favorable outliers, keep the full losses, then stress fees by 0.10 R.
        return float(mean(min(2.0, setup.realized_r) for setup in group)) - 0.10

    earlier_r, holdout_r = stressed_mean(earlier), stressed_mean(holdout)
    if min(earlier_r, holdout_r) < 0.15:
        return None
    return {
        "earlier_samples": len(earlier), "holdout_samples": len(holdout),
        "earlier_stressed_mean_r": round(earlier_r, 4),
        "holdout_stressed_mean_r": round(holdout_r, 4),
    }
