from __future__ import annotations


class EmergencyStopStore:
    """Account-scoped emergency stop state; default is clear and isolation is explicit."""

    def __init__(self):
        self._blocked: set[tuple[str, str]] = set()

    def set_blocked(self, *, user_id: str, account_id: str, blocked: bool) -> None:
        key = (user_id, account_id)
        if blocked:
            self._blocked.add(key)
        else:
            self._blocked.discard(key)

    def is_blocked(self, *, user_id: str, account_id: str) -> bool:
        return (user_id, account_id) in self._blocked
