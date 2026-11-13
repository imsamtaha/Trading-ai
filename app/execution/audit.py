from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class ExecutionAuditEvent:
    user_id: str
    account_id: str
    mode: str
    outcome: str
    reason: str
    timestamp: str


class ExecutionAuditLog:
    """Credential-free execution audit sink with an in-memory default implementation."""

    def __init__(self):
        self._events: list[ExecutionAuditEvent] = []

    def record(self, *, user_id: str, account_id: str, mode: str, outcome: str, reason: str) -> None:
        self._events.append(ExecutionAuditEvent(
            user_id=user_id,
            account_id=account_id,
            mode=mode,
            outcome=outcome,
            reason=reason,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ))

    def events(self) -> list[dict[str, Any]]:
        return [asdict(event) for event in self._events]
