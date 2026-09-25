from fastapi.testclient import TestClient
import pytest

from app.customer.service import customer_service
from app.main import app

client = TestClient(app)


class FakeRuntime:
    def __init__(self): self.calls = []
    def run(self, *, customer_id, account_id, symbol, timeframe, demo_volume, requested_risk_pct):
        self.calls.append((customer_id, account_id, symbol, timeframe, demo_volume, requested_risk_pct))
        return {
            "status": "EXECUTED", "trace_id": "runtime-trace", "decision": "BUY",
            "confidence": 0.73, "rescue": "HOLD",
            "execution": {"broker_result": {"ticket": 9001, "symbol": symbol}},
            "notification": {"trace_id": "runtime-trace", "event": "EXECUTION"},
            "agents": ["technical", "regime", "system_watchdog"],
        }


@pytest.fixture(autouse=True)
def _auth(monkeypatch):
    monkeypatch.setattr("app.customer.api.router.verify_supabase_access_token", lambda value: "c1")


def setup_function():
    customer_service.reset()
    customer_service.register_account("c1", "a1", tier="PRO", auth_subject="c1")


def test_cycle_demo_invokes_runtime_and_updates_customer_read_model(monkeypatch):
    runtime = FakeRuntime()
    monkeypatch.setattr(customer_service, "demo_runtime", runtime)
    response = client.post(
        "/api/v2/customer/cycle/demo",
        headers={"X-Customer-ID":"c1", "X-Account-ID":"a1", "Authorization":"Bearer token"},
        json={"symbol":"EURUSD", "timeframe":"5m", "demo_volume":0.1, "requested_risk_pct":1.0},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "EXECUTED"
    assert runtime.calls == [("c1", "a1", "EURUSD", "5m", 0.1, 1.0)]
    assert customer_service.latest_decision("c1", "a1")["trace_id"] == "runtime-trace"
    assert customer_service.list_positions("c1", "a1")[0]["ticket"] == 9001
    assert customer_service.agent_status[("c1", "a1")]["agents"] == ["technical", "regime", "system_watchdog"]
