from fastapi.testclient import TestClient

from app.dashboard import _atlas_ultimate_html
from app.dashboard.fxpro_onboarding import DEFAULT_FXPRO_URL, fxpro_open_account_url
from app.main import app


def test_dashboard_exposes_fxpro_mobile_entry():
    html = _atlas_ultimate_html()
    assert "FXPRO MOBILE ENTRY" in html
    assert 'href="/connect/fxpro"' in html


def test_fxpro_mobile_entry_is_available_in_dashboard_only_mode(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    client = TestClient(app)

    response = client.get("/connect/fxpro")

    assert response.status_code == 200
    assert "FxPro → ATLAS" in response.text
    assert 'inputmode="numeric"' in response.text
    assert 'name="password"' not in response.text.lower()
    assert "Do not enter your FxPro password" in response.text


def test_fxpro_partner_url_can_be_configured_without_code_change(monkeypatch):
    partner_url = "https://partner.example.test/fxpro/ref-123"
    monkeypatch.setenv("ATLAS_FXPRO_PARTNER_URL", partner_url)
    assert fxpro_open_account_url() == partner_url


def test_fxpro_partner_url_rejects_non_https_values(monkeypatch):
    monkeypatch.setenv("ATLAS_FXPRO_PARTNER_URL", "javascript:alert(1)")
    assert fxpro_open_account_url() == DEFAULT_FXPRO_URL
