from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_dashboard_includes_agent_panel_script(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert '/ui/agent-panel.js' in response.text
    assert '/ui/preferences.js' in response.text


def test_agent_panel_script_is_read_only_ui(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    response = client.get("/ui/agent-panel.js")
    assert response.status_code == 200
    assert "/agent/decision" in response.text
    assert "/agent/paper/execute" not in response.text
    assert "/mt5/test-order" not in response.text
    assert "No MT5 order" in response.text
    assert 'value=\"multi\" selected' in response.text
    assert "multi_timeframe:" in response.text
    assert "data.timeframe_decisions" in response.text
    assert "esc(f.decision)" in response.text
