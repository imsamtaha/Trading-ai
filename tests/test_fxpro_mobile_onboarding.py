from fastapi.testclient import TestClient

from app.dashboard import _atlas_ultimate_html
from app.dashboard.fxpro_onboarding import (
    DEFAULT_FXPRO_URL,
    FXPRO_CONNECT_PATH,
    LEGACY_FXPRO_CONNECT_PATH,
    fxpro_open_account_url,
)
from app.main import app


def test_dashboard_exposes_fxpro_mt5_entry():
    html = _atlas_ultimate_html()
    assert "FXPRO MT5 ENTRY" in html
    assert "Connect with FxPro MT5" in html
    assert f'href="{FXPRO_CONNECT_PATH}"' in html


def test_fxpro_mt5_entry_is_available_in_dashboard_only_mode(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    client = TestClient(app)

    response = client.get(FXPRO_CONNECT_PATH)

    assert response.status_code == 200
    assert "Connect with FxPro MT5" in response.text
    assert "Demo · Read-only onboarding" in response.text
    assert 'inputmode="numeric"' in response.text
    assert 'name="password"' not in response.text.lower()
    assert "Do not enter your FxPro password" in response.text
    assert "atlas.fxpro.mt5.connectionDraft" in response.text


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
