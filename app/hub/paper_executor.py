from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class PaperPosition:
    symbol: str
    side: str
    volume: float
    entry: float
    stop_loss: float | None = None
    take_profit: float | None = None
    opened_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PaperExecutor:
    """Minimal in-memory execution adapter for safe Trading Hub MVP tests."""

    def __init__(self) -> None:
        self.positions: list[PaperPosition] = []

    def execute(self, decision: dict[str, Any], price: float, volume: float = 0.01) -> dict[str, Any]:
        action = str(decision.get("action", "WAIT")).upper()
        if not decision.get("approved") or action not in {"BUY", "SELL"}:
            return {"status": "SKIPPED", "reason": decision.get("reason", "decision not approved")}

        position = PaperPosition(
            symbol=str(decision["symbol"]).upper(),
            side=action,
            volume=float(volume),
            entry=float(price),
            stop_loss=decision.get("stop_loss"),
            take_profit=decision.get("take_profit"),
        )
        self.positions.append(position)
        return {"status": "OPENED", "position": position.__dict__.copy()}

    def snapshot(self) -> list[dict[str, Any]]:
        return [position.__dict__.copy() for position in self.positions]
