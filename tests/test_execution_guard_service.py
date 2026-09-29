from datetime import UTC, datetime, timedelta
from app.execution_guard.models import CouncilDecision


class Repo:
    def __init__(self):
        self.events = []
        self.drafts = {}
    def add_execution_guard_event(self, user_id, payload):
        self.events.append({"user_id": user_id, **payload}); return self.events[-1]
    def save_trade_draft(self, user_id, payload):
        self.drafts[(user_id, payload["draft_id"])] = payload; return payload
    def get_trade_draft(self, user_id, draft_id):
        return self.drafts.get((user_id, draft_id))


class MT5:
    def __init__(self, mode="DEMO", demo_enabled=True):
        self.mode, self.demo_enabled, self.orders = mode, demo_enabled, []
    def get_dashboard_state(self, user_id):
        return {"connected": True, "account": {"account_type": self.mode, "account_masked": "***1234"}, "symbols": [{"symbol": "EURUSD", "price": 1.10}]}
    def manual_trading_state(self, user_id):
        return {"connected": True, "active": self.demo_enabled, "account_type": self.mode, "account_masked": "***1234"}
    def place_manual_order(self, user_id, order):
        self.orders.append(order); return {"status": "FILLED", "ticket": 42}


def decision(direction="BUY", confidence=80, age_seconds=0, decision_id="decision-001"):
    now = datetime.now(UTC)
    return CouncilDecision(
        decision_id=decision_id, symbol="EURUSD", direction=direction,
        confidence=confidence, rationale="Council approved", timestamp=now - timedelta(seconds=age_seconds),
        volume=None if direction == "WAIT" else 0.01,
        stop_loss=None if direction == "WAIT" else (1.09 if direction == "BUY" else 1.11),
        take_profit=None if direction == "WAIT" else (1.11 if direction == "BUY" else 1.09),
        risk_context={},
    )


def test_blocks_wait_low_confidence_stale_and_invalid_levels():
    from app.execution_guard.service import ExecutionGuardService
    repo, mt5 = Repo(), MT5()
    service = ExecutionGuardService(repo, mt5)
    cases = [
        decision("WAIT"), decision(confidence=50, decision_id="decision-002"),
        decision(age_seconds=999, decision_id="decision-003"),
        CouncilDecision(**{**decision(decision_id="decision-004").model_dump(), "stop_loss": 1.12}),
    ]
    for item in cases:
        result = service.evaluate("alice", item)
        assert result.status == "BLOCKED"
    assert mt5.orders == []


def test_demo_executes_once_when_enabled_and_real_creates_draft_only():
    from app.execution_guard.service import ExecutionGuardService
    repo = Repo()
    demo = MT5("DEMO", demo_enabled=True)
    result = ExecutionGuardService(repo, demo).evaluate("alice", decision())
    assert result.status == "EXECUTED"
    assert len(demo.orders) == 1
    duplicate = ExecutionGuardService(repo, demo).evaluate("alice", decision())
    assert duplicate.status == "BLOCKED"
    assert len(demo.orders) == 1

    real = MT5("REAL", demo_enabled=True)
    draft_result = ExecutionGuardService(Repo(), real).evaluate("alice", decision(decision_id="decision-real"))
    assert draft_result.status == "WAITING_CONFIRMATION"
    assert real.orders == []


def test_demo_execution_disabled_blocks_without_broker_call():
    from app.execution_guard.service import ExecutionGuardService
    mt5 = MT5("DEMO", demo_enabled=False)
    result = ExecutionGuardService(Repo(), mt5).evaluate("alice", decision())
    assert result.status == "BLOCKED"
    assert mt5.orders == []
