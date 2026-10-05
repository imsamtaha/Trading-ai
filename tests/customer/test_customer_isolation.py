from fastapi.testclient import TestClient
import pytest

from app.customer.service import customer_service
from app.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def _fake_auth(monkeypatch):
    # Exercise private-route identity isolation independently of the public guard.
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "false")
    def verify(value):
        if not value or not value.startswith("Bearer "):
            raise ValueError("missing bearer token")
        return value.removeprefix("Bearer ")
    monkeypatch.setattr("app.customer.api.router.verify_supabase_access_token", verify, raising=False)


def setup_function():
    customer_service.reset()
    customer_service.register_account("c1", "a1", tier="PRO")
    customer_service.register_account("c2", "a2", tier="PRO")
    customer_service.add_position("c1", "a1", {"ticket": 1, "symbol": "EURUSD"})
    customer_service.add_position("c2", "a2", {"ticket": 2, "symbol": "GBPUSD"})
    customer_service.add_alert("c1", "a1", {"trace_id": "trace-c1", "event": "TEST"})
    customer_service.add_audit("c1", "a1", "trace-c1", {"event": "ONLY_C1"})


def _h(customer, account):
    return {"X-Customer-ID": customer, "X-Account-ID": account, "Authorization": f"Bearer {customer}"}


def test_positions_and_alerts_are_scoped_to_request_identity():
    c2_positions = client.get("/api/v2/customer/positions", headers=_h("c2", "a2")).json()["positions"]
    assert [p["ticket"] for p in c2_positions] == [2]
    c2_alerts = client.get("/api/v2/customer/alerts", headers=_h("c2", "a2")).json()["alerts"]
    assert c2_alerts == []


def test_valid_trace_owned_by_other_customer_is_not_disclosed():
    response = client.get("/api/v2/internal/audit/trace-c1", headers=_h("c2", "a2"))
    assert response.status_code == 404


def test_dashboard_only_mode_blocks_internal_audit_even_for_owner(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    response = client.get("/api/v2/internal/audit/trace-c1", headers=_h("c1", "a1"))
    assert response.status_code == 403
    assert "ONLY_C1" not in response.text


def test_mismatched_account_identity_is_rejected():
    response = client.get("/api/v2/customer/account", headers=_h("c1", "a2"))
    assert response.status_code == 403


def test_missing_authentication_is_rejected():
    response = client.get("/api/v2/customer/account", headers={"X-Customer-ID": "c1", "X-Account-ID": "a1"})
    assert response.status_code == 401


def test_authenticated_subject_cannot_spoof_another_customer():
    headers = {"X-Customer-ID": "c1", "X-Account-ID": "a1", "Authorization": "Bearer c2"}
    response = client.get("/api/v2/customer/account", headers=headers)
    assert response.status_code == 403
