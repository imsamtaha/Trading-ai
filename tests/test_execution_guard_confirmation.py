from datetime import UTC, datetime, timedelta
import pytest
from app.execution_guard.service import ExecutionGuardService
from app.users.repository import MemoryUserRepository


class LiveMT5:
    def __init__(self):
        self.orders = []
        self.mode = "REAL"
        self.account_masked = "***1234"
        self.raise_unknown = False
    def get_dashboard_state(self, user_id):
        return {"connected": True, "account": {"account_type": self.mode, "account_masked": self.account_masked}, "symbols": [{"symbol": "EURUSD", "price": 1.10}]}
    def place_manual_order(self, user_id, order):
        self.orders.append(order)
        if self.raise_unknown:
            raise RuntimeError("broker timeout")
        return {"status": "FILLED", "ticket": 77}


def seed(repo, user_id="alice", expires_delta=120, status="WAITING_CONFIRMATION"):
    payload = {
        "draft_id": "draft-confirm-1", "user_id": user_id, "decision_id": "decision-live-1",
        "account_masked": "***1234", "account_type": "REAL", "symbol": "EURUSD",
        "direction": "BUY", "volume": 0.01, "stop_loss": 1.09, "take_profit": 1.11,
        "confidence": 84.0, "rationale": "Council consensus",
        "expires_at": (datetime.now(UTC) + timedelta(seconds=expires_delta)).isoformat(),
        "status": status, "council_evidence": {}, "risk_result": {"status": "READY"},
    }
    repo.save_trade_draft(user_id, payload)
    return payload


def test_confirm_rejects_wrong_user_expired_consumed_and_changed_account():
    repo, mt5 = MemoryUserRepository(), LiveMT5()
    seed(repo)
    service = ExecutionGuardService(repo, mt5)
    with pytest.raises(ValueError): service.confirm("bob", "draft-confirm-1")
    repo = MemoryUserRepository(); seed(repo, expires_delta=-1)
    with pytest.raises(ValueError): ExecutionGuardService(repo, mt5).confirm("alice", "draft-confirm-1")
    repo = MemoryUserRepository(); seed(repo, status="CONSUMED")
    with pytest.raises(ValueError): ExecutionGuardService(repo, mt5).confirm("alice", "draft-confirm-1")
    repo = MemoryUserRepository(); seed(repo); mt5.account_masked = "***9999"
    with pytest.raises(ValueError): ExecutionGuardService(repo, mt5).confirm("alice", "draft-confirm-1")


def test_valid_confirmation_submits_once_and_consumes_draft():
    repo, mt5 = MemoryUserRepository(), LiveMT5()
    seed(repo)
    service = ExecutionGuardService(repo, mt5)
    result = service.confirm("alice", "draft-confirm-1")
    assert result["status"] == "FILLED"
    assert len(mt5.orders) == 1
    assert repo.get_trade_draft("alice", "draft-confirm-1")["status"] == "CONSUMED"
    with pytest.raises(ValueError): service.confirm("alice", "draft-confirm-1")
    assert len(mt5.orders) == 1


def test_unknown_broker_outcome_is_recorded_without_retry():
    repo, mt5 = MemoryUserRepository(), LiveMT5()
    seed(repo)
    mt5.raise_unknown = True
    service = ExecutionGuardService(repo, mt5)
    with pytest.raises(RuntimeError): service.confirm("alice", "draft-confirm-1")
    assert len(mt5.orders) == 1
    assert repo.get_trade_draft("alice", "draft-confirm-1")["status"] == "UNKNOWN"
    assert any(e["status"] == "UNKNOWN" for e in repo.list_execution_guard_events("alice"))
