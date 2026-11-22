from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


ACCOUNT_TRADE_MODE_DEMO = 0
ACCOUNT_TRADE_MODE_CONTEST = 1
ACCOUNT_TRADE_MODE_REAL = 2


class ExecutionMode(str, Enum):
    PAPER = "paper"
    LIVE_DEMO = "live_demo"
    LIVE_EXECUTION = "live_execution"


@dataclass(frozen=True)
class ExecutionContext:
    user_id: str
    account_id: str
    mode: ExecutionMode
    is_owner: bool = False


class ExecutionAuthorizationError(ValueError):
    pass


def authorize_execution_context(context: ExecutionContext, broker_account: object | None) -> None:
    """Fail closed unless actor, requested mode and active broker account agree."""
    if context.mode is ExecutionMode.PAPER:
        if not context.is_owner:
            raise ExecutionAuthorizationError("Paper mode is owner-only.")
        return

    if broker_account is None:
        raise ExecutionAuthorizationError("Broker account metadata is required.")

    try:
        active_login = int(getattr(broker_account, "login"))
        expected_login = int(context.account_id)
        trade_mode = int(getattr(broker_account, "trade_mode"))
    except (TypeError, ValueError, AttributeError):
        raise ExecutionAuthorizationError("Broker account metadata is invalid.") from None

    if active_login != expected_login:
        raise ExecutionAuthorizationError("Active broker account does not match the authorized account.")
    if not bool(getattr(broker_account, "trade_allowed", False)):
        raise ExecutionAuthorizationError("The active broker account does not allow trading.")

    required_mode = (
        ACCOUNT_TRADE_MODE_DEMO
        if context.mode is ExecutionMode.LIVE_DEMO
        else ACCOUNT_TRADE_MODE_REAL
    )
    if trade_mode != required_mode:
        raise ExecutionAuthorizationError("Active broker account does not match the requested execution mode.")
