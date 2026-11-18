"""ATLAS owner-only access to OmniRoute research, no public order path."""
from fastapi.testclient import TestClient

from app.main import app


def _paper_owner(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    monkeypatch.setenv("ATLAS_LIVE_TRADING", "false")
    monkeypatch.setenv("ATLAS_REAL_MONEY_EXECUTION", "false")
    monkeypatch.setenv("ATLAS_OWNER_DASHBOARD_USER", "test-owner")
    monkeypatch.setenv("ATLAS_OWNER_DASHBOARD_PASSWORD", "test-only-strong-owner-password-123")
    monkeypatch.delenv("ATLAS_OMNIROUTE_ENABLED", raising=False)


def test_omniroute_status_requires_owner_auth_and_defaults_disabled(monkeypatch):
    _paper_owner(monkeypatch)
    with TestClient(app) as client:
        assert client.get("/sam/api/omniroute/status").status_code == 401
        resp = client.get(
            "/sam/api/omniroute/status",
            auth=("test-owner", "test-only-strong-owner-password-123"),
        )
        assert resp.status_code == 200
        result = resp.json()
        assert result["status"] == "OMNIROUTE_DISABLED"
        assert result["broker_execution_allowed"] is False
        assert result["live_trading_enabled"] is False


def test_private_research_endpoint_never_enables_broker(monkeypatch):
    _paper_owner(monkeypatch)
    payload = {
        "symbol": "XAUUSD", "timeframe": "15m",
        "observations": ["Synthetic trend is unclear; no verified source."],
    }
    with TestClient(app) as client:
        assert client.post("/sam/api/omniroute/research", json=payload).status_code == 401
        resp = client.post(
            "/sam/api/omniroute/research",
            json=payload,
            auth=("test-owner", "test-only-strong-owner-password-123"),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "OMNIROUTE_DISABLED"
        assert resp.json()["broker_execution_allowed"] is False
        assert client.post("/mt5/test-order").status_code == 403


def test_owner_cannot_bypass_safe_mode(monkeypatch):
    _paper_owner(monkeypatch)
    monkeypatch.setenv("ATLAS_LIVE_TRADING", "true")
    with TestClient(app) as client:
        resp = client.get(
            "/sam/api/omniroute/status",
            auth=("test-owner", "test-only-strong-owner-password-123"),
        )
        assert resp.status_code == 503


def test_private_research_works_when_public_analysis_off(monkeypatch):
    _paper_owner(monkeypatch)
    monkeypatch.setenv("ATLAS_PUBLIC_ANALYSIS_ENABLED", "false")
    with TestClient(app) as client:
        response = client.post(
            "/sam/api/omniroute/research",
            json={"symbol": "EURUSD", "timeframe": "1h", "observations": ["Synthetic data only"]},
            auth=("test-owner", "test-only-strong-owner-password-123"),
        )
        assert response.status_code == 200
        assert response.json()["status"] == "OMNIROUTE_DISABLED"


def test_malformed_private_research_symbol_gets_400_not_500(monkeypatch):
    _paper_owner(monkeypatch)
    monkeypatch.setenv("ATLAS_OMNIROUTE_ENABLED", "true")
    monkeypatch.setenv("ATLAS_OMNIROUTE_API_KEY", "synthetic-test-only")
    with TestClient(app) as client:
        resp = client.post(
            "/sam/api/omniroute/research",
            json={"symbol": "XAUUSD?unsafe", "timeframe": "1h", "observations": ["Synthetic only"]},
            auth=("test-owner", "test-only-strong-owner-password-123"),
        )
        assert resp.status_code == 400
        assert "symbol" in resp.json()["detail"]


def test_owner_dashboard_displays_private_omniroute_status(monkeypatch):
    _paper_owner(monkeypatch)
    with TestClient(app) as client:
        assert client.get("/sam").status_code == 401
        response = client.get(
            "/sam",
            auth=("test-owner", "test-only-strong-owner-password-123"),
        )
        assert response.status_code == 200
        assert 'id="omni-status"' in response.text
        assert "/sam/api/omniroute/status" in response.text
