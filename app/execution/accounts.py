from __future__ import annotations

from dataclasses import dataclass


class AccountIsolationError(PermissionError):
    pass


@dataclass(frozen=True)
class ExecutionAccount:
    user_id: str
    account_id: str


class ExecutionAccountRegistry:
    """Minimal ownership registry. Production persistence can implement the same interface."""

    def __init__(self, accounts: list[ExecutionAccount] | None = None):
        self._owners = {item.account_id: item.user_id for item in (accounts or [])}

    def resolve(self, *, user_id: str, account_id: str) -> ExecutionAccount:
        if self._owners.get(account_id) != user_id:
            raise AccountIsolationError("Execution account is not owned by the authenticated user.")
        return ExecutionAccount(user_id=user_id, account_id=account_id)
