import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.billing import router
from app.dashboard.preferences import router as preferences_router
from app.dashboard import atlas_ultimate_view
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
    assert result["provider"] == "Whish Pay"
    assert result["amount_usd"] == 99
    assert result["status"] == "PENDING_REVIEW"
    assert result["access_granted"] is False
    assert result["automatic_renewal"] is False
    assert result["merchant_checkout_active"] is False
    assert c.post("/billing/whish/pro/request", json={"email": "a@example.com"}).json()["reference"] == result["reference"]
    assert c.post("/billing/whish/invalid/request", json={"email": "a@example.com"}).status_code == 404
    assert c.post("/billing/whish/pro/request", json={"email": "invalid"}).status_code == 422


def test_preferences_and_whish_links_are_integrated_in_atlas_ultimate():
    page = atlas_ultimate_view().body
    assert b"/ui/preferences.js" in page
    assert b"/billing/whish/reader" in page and b"/billing/whish/pro" in page
    assert b'id="plans"' in page
    assert b"Pay with Whish Pay" in page
    redirect = subscribe()
    assert redirect.status_code == 308
    assert redirect.headers["location"] == "/#plans"
    c = client()
    assert "/ui/preferences.js" in c.get("/billing/whish/reader").text
    script = c.get("/ui/preferences.js")
    assert script.status_code == 200
    assert "atlas-language" in script.text and "atlas-theme" in script.text


def test_billing_catalog_reports_whish_and_pending_stripe_state():
    methods = client().get("/billing/methods").json()
    assert "whish" in methods
    assert "stripe" in methods
    assert methods["whish"]["provider"] == "Whish Pay"
    assert methods["whish"]["checkout_type"] == "wallet_payment_gateway"
    assert methods["stripe"]["available"] is False
    assert methods["stripe"]["mode"] == "verification_pending"
