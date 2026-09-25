from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_dashboard_uses_realtime_council_instead_of_legacy_agent_panel(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "/ui/customer-v2-panel.js" in response.text
    assert "/ui/agent-panel.js" not in response.text
    assert "ATLAS Intelligence Council" in response.text


def test_legacy_agent_panel_route_is_removed(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "false")
    assert client.get("/ui/agent-panel.js").status_code == 404
