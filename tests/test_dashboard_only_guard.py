"""Exercise the public access boundary without connecting to MT5 or providers."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app import main
from app.dashboard import api
from app.execution.mt5 import MT5Config, MT5ExecutionError


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    monkeypatch.setenv("ATLAS_LIVE_TRADING", "false")
    monkeypatch.setenv("ATLAS_WHISH_ENABLED", "false")
    monkeypatch.setenv("ATLAS_AGENT_PAPER_EXECUTION_ENABLED", "false")
    # A blocked route must never reach market providers or the execution service.
    monkeypatch.setattr(main, "_mt5_service", Mock(side_effect=AssertionError("Execution reached")))
    monkeypatch.setattr(main.MT5Broker, "connect", Mock(side_effect=AssertionError("MT5 reached")))
    monkeypatch.setattr(main, "get_price", Mock(side_effect=AssertionError("Provider reached")))
    return TestClient(main.app)


@pytest.mark.parametrize("path", [
    "/", "/health", "/subscribe",
    "/ui/preferences.js", "/ui/agent-panel.js", "/agent/capabilities",
    "/docs", "/openapi.json", "/billing/plans",
])
def test_public_reads_are_allowed(client, path):
    assert client.get(path).status_code == 200


@pytest.mark.parametrize("path", ["/dashboard/state", "/dashboard/atlas", "/dashboard/mt5-state"])
def test_dashboard_state_reads_telemetry(client, monkeypatch, path):
    broker = Mock()
    broker.connect.return_value = {}
    broker.symbols.return_value = []
    broker.positions.return_value = []
    monkeypatch.setattr(api, "MT5Broker", lambda config: broker)
    monkeypatch.setattr(api, "mt5", SimpleNamespace(account_info=lambda: SimpleNamespace(trade_mode=0)))
    monkeypatch.setattr(api, "SupabaseSignalJournal", Mock())
    monkeypatch.setattr(api._market_intelligence, "snapshot", lambda: {"status": "TEST"})
    response = client.get(path)
    assert response.status_code == 200
    assert response.json()["mode"] == "READ_ONLY"
    assert response.json()["services"]["execution_gate"] == "DISABLED"
    assert MT5Config.from_env().dry_run is True
    broker.disconnect.assert_called_once()


def test_state_offline_response_is_not_replaced_by_guard(client, monkeypatch):
    monkeypatch.setattr(main.MT5Broker, "connect", Mock(side_effect=MT5ExecutionError("Test offline")))
    monkeypatch.setattr(main.MT5Broker, "disconnect", Mock())
    response = client.get("/dashboard/state")
    assert response.status_code == 503
    assert response.json() == {"detail": "Test offline"}


@pytest.mark.parametrize("method,path", [
    ("GET", "/market/EURUSD"), ("GET", "/analysis/EURUSD"),
    ("GET", "/performance/1"), ("GET", "/mt5/status"),
    ("GET", "/mt5/positions"), ("GET", "/mt5/quote/EURUSD"),
    ("POST", "/mt5/test-order"), ("POST", "/agent/paper/execute"),
    ("POST", "/billing/whish/pro/request"), ("GET", "/billing/unknown"),
    ("GET", "/dashboard/unknown"), ("GET", "/dashboard/state/execute"),
    ("GET", "/dashboard-evil"), ("POST", "/mt5/cockpit-state"),
])
def test_non_public_routes_are_forbidden(client, method, path):
    response = client.request(method, path)
    assert response.status_code == 403
    assert response.json() == {"detail": "Dashboard-only mode is enabled."}


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
@pytest.mark.parametrize("path", ["/dashboard", "/dashboard/state", "/dashboard/mt5-state", "/health", "/billing/plans", "/assets/site.js"])
def test_public_paths_do_not_allow_writes(client, method, path):
    assert client.request(method, path).status_code == 403


def test_disabled_guard_passes_through_without_enabling_trading(client, monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "false")
    monkeypatch.setattr(main, "get_price", lambda symbol: {"symbol": symbol})
    response = client.get("/market/EURUSD")
    assert response.status_code == 200
    assert response.json() == {"symbol": "EURUSD"}
    assert MT5Config.from_env().dry_run is True


@pytest.mark.parametrize(
    "path",
    ["/agent/decision", "/agent/right-hand/plan", "/agent/right-hand/chat"],
)
def test_public_analysis_posts_can_be_disabled(client, monkeypatch, path):
    monkeypatch.setenv("ATLAS_PUBLIC_ANALYSIS_ENABLED", "false")

    response = client.post(path)

    assert response.status_code == 403
    assert response.json() == {"detail": "Dashboard-only mode is enabled."}
