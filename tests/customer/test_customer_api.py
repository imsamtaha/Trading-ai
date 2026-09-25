from fastapi.testclient import TestClient

from app.customer.service import customer_service
from app.main import app


client = TestClient(app)


def setup_function():
    customer_service.reset()
    customer_service.register_account("c1", "a1", tier="PRO")
    customer_service.register_account("c2", "a2", tier="ELITE")
    customer_service.add_position("c1", "a1", {"ticket": 1, "symbol": "EURUSD"})
    customer_service.add_alert("c1", "a1", {"trace_id": "trace-c1", "event": "RESCUE"})
    customer_service.add_decision("c1", "a1", {"trace_id": "trace-c1", "decision": "WAIT", "confidence": 0.5})
    customer_service.add_audit("c1", "a1", "trace-c1", {"event": "DECISION"})


def _h(customer="c1", account="a1"):
    return {"X-Customer-ID": customer, "X-Account-ID": account}


def test_customer_v2_endpoints_have_scoped_shapes_and_trace_ids():
    assert client.get("/api/v2/customer/account", headers=_h()).json()["customer_id"] == "c1"
    positions = client.get("/api/v2/customer/positions", headers=_h()).json()
    assert positions["customer_id"] == "c1"
    assert positions["positions"][0]["ticket"] == 1
    latest = client.get("/api/v2/customer/decisions/latest", headers=_h()).json()
    assert latest["trace_id"] == "trace-c1"
    assert client.get("/api/v2/customer/agents/status", headers=_h()).status_code == 200
    assert client.get("/api/v2/customer/alerts", headers=_h()).json()["alerts"][0]["trace_id"] == "trace-c1"
    assert client.get("/api/v2/customer/rescue/status", headers=_h()).status_code == 200
    cycle = client.post("/api/v2/customer/cycle/demo", headers=_h()).json()
    assert cycle["mode"] == "LIVE_DEMO"
    assert cycle["trace_id"]


def test_customer_api_responses_do_not_expose_paper_terminology():
    urls = [
        "/api/v2/customer/account",
        "/api/v2/customer/positions",
        "/api/v2/customer/decisions/latest",
        "/api/v2/customer/agents/status",
        "/api/v2/customer/alerts",
        "/api/v2/customer/rescue/status",
    ]
    for url in urls:
        response = client.get(url, headers=_h())
        assert response.status_code == 200
        assert "paper" not in response.text.lower()


def test_dashboard_only_mode_allows_customer_v2_reads_and_demo_cycle(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    assert client.get("/api/v2/customer/account", headers=_h()).status_code == 200
    response = client.post("/api/v2/customer/cycle/demo", headers=_h())
    assert response.status_code == 200
    assert response.json()["mode"] == "LIVE_DEMO"
