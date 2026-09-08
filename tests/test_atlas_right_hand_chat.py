from fastapi.testclient import TestClient

from app.agent.conversation import converse
from app.main import app


client = TestClient(app)


def test_general_chat_routes_without_claiming_tool_execution():
    result = converse("Review my GitHub repo and identify the next coding tasks")

    assert result.specialist == "coding"
    assert result.status == "PLANNED"
    assert result.execution_mode == "assist"
    assert "will not claim external tools ran" in result.message


def test_market_chat_without_symbol_requests_context():
    result = converse("Analyze the market for a scalping setup")

    assert result.specialist == "market"
    assert result.status == "NEEDS_CONTEXT"
    assert result.execution_mode == "paper_only"
    assert result.approval_required is True
    assert "XAUUSD" in result.result["supported_symbols"]


def test_right_hand_chat_is_available_in_dashboard_only_mode(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    response = client.post(
        "/agent/right-hand/chat",
        json={"request": "Prepare my project priorities for today"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["specialist"] == "executive"
    assert body["status"] == "PLANNED"


def test_right_hand_chat_never_exposes_live_market_execution(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    response = client.post(
        "/agent/right-hand/chat",
        json={"request": "Analyze the market for scalping"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["execution_mode"] == "paper_only"
    assert body["status"] == "NEEDS_CONTEXT"
