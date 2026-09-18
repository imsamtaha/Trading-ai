import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_remote_bridge_client_requires_configured_url(monkeypatch):
    monkeypatch.delenv("ATLAS_MT5_BRIDGE_URL", raising=False)
    from app.integrations.mt5_bridge import RemoteMT5BridgeError, fetch_remote_mt5_telemetry

    with pytest.raises(RemoteMT5BridgeError, match="ATLAS_MT5_BRIDGE_URL"):
        fetch_remote_mt5_telemetry()


def test_remote_bridge_client_fetches_read_only_demo_telemetry(monkeypatch):
    monkeypatch.setenv("ATLAS_MT5_BRIDGE_URL", "http://192.168.1.50:8765")
    monkeypatch.setenv("ATLAS_MT5_BRIDGE_TOKEN", "secret-token")
    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "status": "ONLINE",
                "mode": "READ_ONLY",
                "account": {"account_type": "DEMO", "login": "***1234"},
                "positions": [],
                "quotes": [{"symbol": "EURUSD", "bid": 1.1, "ask": 1.2}],
                "broker_orders": False,
            }

        def raise_for_status(self):
            return None

    def fake_get(url, *, headers, timeout):
        captured.update({"url": url, "headers": headers, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr("app.integrations.mt5_bridge.requests.get", fake_get)

    from app.integrations.mt5_bridge import fetch_remote_mt5_telemetry

    data = fetch_remote_mt5_telemetry()
    assert captured["url"] == "http://192.168.1.50:8765/telemetry"
    assert captured["headers"]["Authorization"] == "Bearer secret-token"
    assert data["account"]["account_type"] == "DEMO"
    assert data["mode"] == "READ_ONLY"
    assert data["broker_orders"] is False


def test_remote_bridge_rejects_non_demo_or_execution_enabled_payload(monkeypatch):
    monkeypatch.setenv("ATLAS_MT5_BRIDGE_URL", "http://127.0.0.1:8765")

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "status": "ONLINE",
                "mode": "LIVE_EXECUTION",
                "account": {"account_type": "REAL"},
                "broker_orders": True,
            }

        def raise_for_status(self):
            return None

    monkeypatch.setattr("app.integrations.mt5_bridge.requests.get", lambda *a, **k: FakeResponse())

    from app.integrations.mt5_bridge import RemoteMT5BridgeError, fetch_remote_mt5_telemetry

    with pytest.raises(RemoteMT5BridgeError, match="demo/read-only"):
        fetch_remote_mt5_telemetry()


def test_dashboard_state_uses_remote_bridge_when_configured(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    monkeypatch.setenv("ATLAS_MT5_BRIDGE_URL", "http://192.168.1.50:8765")
    payload = {
        "status": "ONLINE",
        "timestamp": "2026-09-18T08:00:00+00:00",
        "mode": "READ_ONLY",
        "account": {
            "label": "ATLAS VERIFIED DEMO",
            "login": "***1234",
            "account_type": "DEMO",
            "broker_company": "FxPro",
            "server": "FxPro-MT5 Demo",
            "currency": "USD",
            "balance": 10000.0,
            "equity": 10010.0,
            "floating_profit": 10.0,
            "margin": 0.0,
            "margin_free": 10010.0,
            "margin_level": 0.0,
            "leverage": 100,
            "trade_allowed": True,
        },
        "positions": [],
        "open_positions": 0,
        "floating_position_pnl": 0.0,
        "quotes": [],
        "services": {
            "mt5": "ONLINE",
            "execution_gate": "DISABLED",
            "subscriber_access": "READ_ONLY",
            "telemetry_source": "WINDOWS_MT5_BRIDGE",
        },
        "broker_orders": False,
        "disclaimer": "Read-only demo telemetry.",
    }

    monkeypatch.setattr("app.dashboard.api.fetch_remote_mt5_telemetry", lambda: payload)
    client = TestClient(app)
    response = client.get("/dashboard/state")
    assert response.status_code == 200
    data = response.json()
    assert data["services"]["telemetry_source"] == "WINDOWS_MT5_BRIDGE"
    assert data["account"]["account_type"] == "DEMO"
    assert data["mode"] == "READ_ONLY"
    assert data["broker_orders"] is False


def test_windows_bridge_module_exposes_get_only_routes():
    from scripts.atlas_mt5_telemetry_bridge import app as bridge_app

    routes = {(route.path, tuple(sorted(route.methods or []))) for route in bridge_app.routes}
    assert any(path == "/health" and "GET" in methods for path, methods in routes)
    assert any(path == "/telemetry" and "GET" in methods for path, methods in routes)
    assert not any("POST" in methods or "PUT" in methods or "DELETE" in methods for path, methods in routes if path in {"/health", "/telemetry"})
