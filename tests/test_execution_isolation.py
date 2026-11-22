import pytest

from app.execution.accounts import AccountIsolationError, ExecutionAccount, ExecutionAccountRegistry
from app.execution.emergency_stop import EmergencyStopStore


def test_account_registry_is_scoped_to_authenticated_user():
    registry = ExecutionAccountRegistry([ExecutionAccount(user_id="alice", account_id="100")])
    assert registry.resolve(user_id="alice", account_id="100").account_id == "100"
    with pytest.raises(AccountIsolationError):
        registry.resolve(user_id="bob", account_id="100")
    with pytest.raises(AccountIsolationError):
        registry.resolve(user_id="alice", account_id="999")


def test_emergency_stop_is_isolated_per_user_and_account():
    stops = EmergencyStopStore()
    stops.set_blocked(user_id="alice", account_id="100", blocked=True)
    assert stops.is_blocked(user_id="alice", account_id="100") is True
    assert stops.is_blocked(user_id="alice", account_id="200") is False
    assert stops.is_blocked(user_id="bob", account_id="100") is False
    stops.set_blocked(user_id="alice", account_id="100", blocked=False)
    assert stops.is_blocked(user_id="alice", account_id="100") is False
