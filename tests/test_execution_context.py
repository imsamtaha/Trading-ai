from types import SimpleNamespace

import pytest

from app.execution.context import (
    ExecutionAuthorizationError,
    ExecutionContext,
    ExecutionMode,
    authorize_execution_context,
)


def account(login: int, trade_mode: int, trade_allowed: bool = True):
    return SimpleNamespace(login=login, trade_mode=trade_mode, trade_allowed=trade_allowed)


def test_owner_can_use_private_paper_without_broker_account():
    ctx = ExecutionContext(user_id="owner", account_id="paper", mode=ExecutionMode.PAPER, is_owner=True)
    authorize_execution_context(ctx, None)


def test_customer_cannot_use_paper():
    ctx = ExecutionContext(user_id="u1", account_id="paper", mode=ExecutionMode.PAPER, is_owner=False)
    with pytest.raises(ExecutionAuthorizationError):
        authorize_execution_context(ctx, None)


def test_live_demo_requires_matching_demo_account():
    ctx = ExecutionContext(user_id="u1", account_id="101", mode=ExecutionMode.LIVE_DEMO, is_owner=False)
    authorize_execution_context(ctx, account(101, 0))
    with pytest.raises(ExecutionAuthorizationError):
        authorize_execution_context(ctx, account(101, 2))


def test_live_execution_requires_matching_real_account():
    ctx = ExecutionContext(user_id="u1", account_id="202", mode=ExecutionMode.LIVE_EXECUTION, is_owner=False)
    authorize_execution_context(ctx, account(202, 2))
    with pytest.raises(ExecutionAuthorizationError):
        authorize_execution_context(ctx, account(202, 0))


def test_contest_unknown_mismatch_and_trading_disabled_fail_closed():
    ctx = ExecutionContext(user_id="u1", account_id="303", mode=ExecutionMode.LIVE_EXECUTION, is_owner=False)
    for broker_account in (
        account(303, 1),
        account(303, -1),
        account(999, 2),
        account(303, 2, False),
        None,
    ):
        with pytest.raises(ExecutionAuthorizationError):
            authorize_execution_context(ctx, broker_account)
