import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.billing import router
from app.dashboard.preferences import router as preferences_router
from app.dashboard.views import dashboard_view
from app.subscription import router as subscription_router, subscribe


def client():
    app = FastAPI()
    app.include_router(subscription_router)
    app.include_router(router)
    app.include_router(preferences_router)
    return TestClient(app)


def test_whish_disabled_until_recipient_configured(monkeypatch):
    monkeypatch.setenv("ATLAS_WHISH_ENABLED", "false")
    assert client().post("/billing/whish/signals/request", json={"email": "a@example.com"}).status_code == 503


def test_whish_persists_pending_request_without_granting_access(tmp_path, monkeypatch):
    monkeypatch.setenv("ATLAS_WHISH_ENABLED", "true")
    monkeypatch.setenv("ATLAS_WHISH_RECIPIENT", "Test merchant")
    monkeypatch.setenv("ATLAS_WHISH_SUPPORT", "support@example.com")
    monkeypatch.setenv("ATLAS_WHISH_DB", str(tmp_path / "whish.db"))
    c = client()
    result = c.post("/billing/whish/signals/request", json={"email": "a@example.com"}).json()
    assert result["amount_usd"] == 99
    assert result["status"] == "PENDING_REVIEW"
    assert result["access_granted"] is False
    assert result["automatic_renewal"] is False
    assert c.post("/billing/whish/signals/request", json={"email": "a@example.com"}).json()["reference"] == result["reference"]
    assert c.post("/billing/whish/execution/request", json={"email": "a@example.com"}).json()["amount_usd"] == 149
    assert c.post("/billing/whish/invalid/request", json={"email": "a@example.com"}).status_code == 404
    assert c.post("/billing/whish/execution/request", json={"email": "invalid"}).status_code == 422


def test_preferences_on_all_pages_and_whish_subscription_methods():
    assert b"/ui/preferences.js" in dashboard_view().body
    page = subscribe().body
    assert b"FREE ACCOUNT" in page and b"/login" in page
    assert b"ATLAS Starter" in page and b"$99" in page
    assert b"ATLAS Pro" in page and b"$149" in page
    assert b"ATLAS Elite" in page and b"$299" in page
    assert b"No broker orders are submitted" in page
    assert b"/billing/whish/starter" in page and b"/billing/whish/pro" in page and b"/billing/whish/elite" in page
    c = client()
    whish_page = c.get("/billing/whish/pro").text
    assert "$149/month" in whish_page
    assert "No plan submits real-money broker orders" in whish_page
    assert "/ui/preferences.js" in whish_page
    script = c.get("/ui/preferences.js")
    assert script.status_code == 200
    assert "atlas-language" in script.text and "atlas-theme" in script.text


def test_subscription_request_records_selected_whish_plan(tmp_path, monkeypatch):
    requests_file = tmp_path / "subscription_requests.jsonl"
    monkeypatch.setenv("ATLAS_SUBSCRIPTION_REQUESTS_FILE", str(requests_file))
    c = client()

    result = c.post(
        "/subscription/request",
        json={"name": "Test Trader", "email": "trader@example.com", "plan": "pro"},
    )

    assert result.status_code == 200
    payload = result.json()
    assert payload["status"] == "PENDING_REVIEW"
    assert payload["whish_url"] == "/billing/whish/pro"
    stored = requests_file.read_text(encoding="utf-8")
    assert '"plan": "pro"' in stored
    assert '"amount_usd": 149' in stored
    assert '"payment_required_now": true' in stored


def test_mt5_access_request_records_read_only_pending_state(tmp_path, monkeypatch):
    requests_file = tmp_path / "mt5_access_requests.jsonl"
    monkeypatch.setenv("ATLAS_MT5_ACCESS_REQUESTS_FILE", str(requests_file))
    c = client()

    result = c.post(
        "/subscription/mt5-request",
        json={
            "name": "Test Trader",
            "email": "trader@example.com",
            "broker": "FxPro",
            "account_number": "592031391",
            "server": "FxPro-MT5 Demo",
        },
    )

    assert result.status_code == 200
    payload = result.json()
    assert payload["status"] == "PENDING_READ_ONLY_CONNECTION"
    assert "trading password" in payload["message"]
    stored = requests_file.read_text(encoding="utf-8")
    assert '"broker": "FxPro"' in stored
    assert '"password_collected": false' in stored
    assert '"live_trading_enabled": false' in stored


def test_billing_catalog_is_whish_only():
    c = client()
    assert "whish" in c.get("/billing/methods").json()
    assert "stripe" not in c.get("/billing/methods").text.lower()
