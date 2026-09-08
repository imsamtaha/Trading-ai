from fastapi.testclient import TestClient

from app.agent.right_hand import build_right_hand_plan, route_request
from app.main import app


client = TestClient(app)


def test_routes_market_request_to_market_specialist():
    assert route_request("Analyze gold scalping conditions") == "market"


def test_routes_code_request_to_tech_copilot():
    assert route_request("Debug this FastAPI error") == "coding"


def test_market_plan_is_paper_only_and_blocks_live_mt5():
    plan = build_right_hand_plan("Analyze EURUSD scalping setup").to_dict()
    assert plan["primary_specialist"] == "market"
    assert plan["execution_mode"] == "paper_only"
    assert plan["approval_required"] is True
    assert any("Do not route live orders to MT5" in item for item in plan["constraints"])


def test_right_hand_capabilities_are_available_in_dashboard_only(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    response = client.get("/agent/right-hand/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "ATLAS Right Hand Agent"
    assert data["safety"]["market_execution"] == "paper_only"
    assert data["safety"]["live_mt5_from_right_hand"] is False


def test_right_hand_plan_is_available_in_dashboard_only(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    response = client.post(
        "/agent/right-hand/plan",
        json={"request": "Prepare my project priorities and follow-ups"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["primary_specialist"] == "executive"
    assert data["metadata"]["version"] == "right-hand-v2"
