from fastapi.testclient import TestClient

from app.dashboard.fxpro_onboarding import (
    DEFAULT_FXPRO_URL,
    FXPRO_CONNECT_PATH,
    LEGACY_FXPRO_CONNECT_PATH,
    fxpro_open_account_url,
)
from app.main import app


def test_fxpro_mt5_entry_is_available_in_dashboard_only_mode(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    client = TestClient(app)

    response = client.get(FXPRO_CONNECT_PATH)

    assert response.status_code == 200
    assert "Connect with FxPro MT5" in response.text
    assert "LIVE DEMO · MT5 CONNECTED" in response.text
    assert 'inputmode="numeric"' in response.text
    assert 'name="password"' not in response.text.lower()
    assert "Do not enter your FxPro password" in response.text
    assert "atlas.fxpro.mt5.connectionDraft" in response.text
    assert "FxPro MT5 Live Demo is connected." in response.text
    assert "Cache-Control" not in response.text
    assert response.headers["cache-control"].startswith("no-store")


def test_legacy_fxpro_mobile_path_redirects_to_mt5_entry(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    client = TestClient(app, follow_redirects=False)

    response = client.get(LEGACY_FXPRO_CONNECT_PATH)

    assert response.status_code == 308
    assert response.headers["location"] == FXPRO_CONNECT_PATH


def test_fxpro_partner_url_can_be_configured_without_code_change(monkeypatch):
    partner_url = "https://partner.example.test/fxpro/ref-123"
    monkeypatch.setenv("ATLAS_FXPRO_PARTNER_URL", partner_url)
    assert fxpro_open_account_url() == partner_url


def test_fxpro_partner_url_rejects_non_https_values(monkeypatch):
    monkeypatch.setenv("ATLAS_FXPRO_PARTNER_URL", "javascript:alert(1)")
    assert fxpro_open_account_url() == DEFAULT_FXPRO_URL


def _connected_demo_account():
    return {
        "connected": True,
        "mode": "LIVE_DEMO",
        "broker_orders": False,
        "demo_execution": True,
        "login": "592031391",
        "masked_login": "***1391",
        "server": "FxPro-MT5 Demo",
        "company": "FxPro Markets Ltd.",
        "balance": 10000.0,
        "equity": 10012.5,
    }


def test_fxpro_mt5_status_reports_connected_demo_without_full_login(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    monkeypatch.setattr(
        "app.dashboard.fxpro_onboarding.current_fxpro_demo_account",
        _connected_demo_account,
    )
    client = TestClient(app)

    response = client.get(FXPRO_CONNECT_PATH + "/status")

    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True
    assert data["masked_login"] == "***1391"
    assert "login" not in data
    assert data["broker_orders"] is False
    assert data["demo_execution"] is True


def test_fxpro_mt5_verify_matches_connected_demo(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    monkeypatch.setattr(
        "app.dashboard.fxpro_onboarding.current_fxpro_demo_account",
        _connected_demo_account,
    )
    client = TestClient(app)

    response = client.post(
        FXPRO_CONNECT_PATH + "/verify",
        json={"login": "592031391", "server": "FxPro-MT5 Demo"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["verified"] is True
    assert data["mode"] == "LIVE_DEMO"
    assert data["broker_orders"] is False
    assert data["demo_execution"] is True
    assert data["masked_login"] == "***1391"
    assert data["balance"] == 10000.0


def test_fxpro_mt5_verify_rejects_different_demo_account(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    monkeypatch.setattr(
        "app.dashboard.fxpro_onboarding.current_fxpro_demo_account",
        _connected_demo_account,
    )
    client = TestClient(app)

    response = client.post(
        FXPRO_CONNECT_PATH + "/verify",
        json={"login": "11112222", "server": "FxPro-MT5 Demo"},
    )

    assert response.status_code == 409
    assert "does not match" in response.json()["detail"]
