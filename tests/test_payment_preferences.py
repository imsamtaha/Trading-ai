import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.billing import router
from app.dashboard.preferences import router as preferences_router
from app.dashboard.views import dashboard_view
from app.subscription import subscribe


def client():
    app = FastAPI()
    app.include_router(router)
    app.include_router(preferences_router)
    return TestClient(app)


def test_whish_disabled_until_recipient_configured(monkeypatch):
    monkeypatch.setenv("ATLAS_WHISH_ENABLED", "false")
    assert client().post("/billing/whish/reader/request", json={"email": "a@example.com"}).status_code == 503


def test_whish_persists_pending_request_without_granting_access(tmp_path, monkeypatch):
    monkeypatch.setenv("ATLAS_WHISH_ENABLED", "true")
    monkeypatch.setenv("ATLAS_WHISH_RECIPIENT", "Test merchant")
    monkeypatch.setenv("ATLAS_WHISH_SUPPORT", "support@example.com")
    monkeypatch.setenv("ATLAS_WHISH_DB", str(tmp_path / "whish.db"))
    c = client()
    result = c.post("/billing/whish/pro/request", json={"email": "a@example.com"}).json()
    assert result["amount_usd"] == 99
    assert result["status"] == "PENDING_REVIEW"
    assert result["access_granted"] is False
    assert result["automatic_renewal"] is False
    assert c.post("/billing/whish/pro/request", json={"email": "a@example.com"}).json()["reference"] == result["reference"]
    assert c.post("/billing/whish/invalid/request", json={"email": "a@example.com"}).status_code == 404
    assert c.post("/billing/whish/pro/request", json={"email": "invalid"}).status_code == 422


def test_preferences_on_all_pages_and_whish_links():
    assert b"/ui/preferences.js" in dashboard_view().body
    page = subscribe().body
    assert b"/billing/whish/reader" in page and b"/billing/whish/pro" in page
    assert page.count(b'/ui/preferences.js') == 1
    c = client()
    assert "/ui/preferences.js" in c.get("/billing/whish/reader").text
    script = c.get("/ui/preferences.js")
    assert script.status_code == 200
    assert "atlas-language" in script.text and "atlas-theme" in script.text


def test_billing_catalog_is_whish_only():
    c = client()
    assert "whish" in c.get("/billing/methods").json()
    assert "stripe" not in c.get("/billing/methods").text.lower()
