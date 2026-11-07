import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient

from app.dashboard import _atlas_ultimate_html
from app.main import app


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required to parse browser JavaScript")
def test_served_active_setups_script_parses_as_javascript():
    response = TestClient(app).get("/ui/setups-panel.js")
    assert response.status_code == 200
    result = subprocess.run(
        ["node", "--check"], input=response.text, text=True, capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr


def test_dashboard_loads_active_setups_panel_script():
    html = _atlas_ultimate_html()
    assert '/ui/setups-panel.js' in html


def test_active_setups_endpoint_is_live_demo_and_available(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    payload = {
        "mode": "LIVE_DEMO",
        "broker_orders": False,
        "demo_execution": True,
        "execution": "simulated_demo",
        "strategy_mode": "BALANCED",
        "interval": "15m",
        "active_count": 1,
        "watch_count": 0,
        "errors": 0,
        "setups": [
            {
                "symbol": "EURUSD",
                "status": "ACTIVE_SETUP",
                "qualified": True,
                "direction": "LONG",
                "confidence": 80.0,
            }
        ],
        "watchlist": [],
        "scanned": 1,
    }


    monkeypatch.setattr("app.dashboard.setups_panel._scan_setups", lambda: payload)
    monkeypatch.setattr("app.dashboard.setups_panel._CACHE", {"expires_at": 0.0, "payload": None})

    client = TestClient(app)
    response = client.get("/dashboard/active-setups")

    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "LIVE_DEMO"
    assert data["broker_orders"] is False
    assert data["demo_execution"] is True
    assert data["execution"] == "simulated_demo"
    assert data["setups"][0]["symbol"] == "EURUSD"

    script = client.get("/ui/setups-panel.js")
    assert script.status_code == 200
    assert "ATLAS Live Demo Setup Engine" in script.text
