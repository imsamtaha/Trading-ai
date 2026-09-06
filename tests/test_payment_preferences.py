import hashlib
import hmac
import json
import time
from types import SimpleNamespace
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.billing import router
from app.billing.stripe_checkout import StripeBilling, BillingProviderError
from app.dashboard.preferences import router as preferences_router
from app.dashboard.views import dashboard_view
from app.subscription import subscribe


def client():
    app = FastAPI()
    app.include_router(router)
    app.include_router(preferences_router)
    return TestClient(app)


def test_valid_webhook_without_api_key_and_tampered_body_rejected():
    secret = "test_signing_secret"
    payload = json.dumps({"id": "evt_test", "object": "event", "type": "customer.subscription.updated"}).encode()
    now = int(time.time())
    signature = hmac.new(secret.encode(), str(now).encode()+b"."+payload, hashlib.sha256).hexdigest()
    billing = StripeBilling(secret_key="", webhook_secret=secret)
    assert billing.construct_event(payload, f"t={now},v1={signature}")["id"] == "evt_test"
    with pytest.raises(BillingProviderError):
        billing.construct_event(payload+b" ", f"t={now},v1={signature}")


def test_unknown_subscription_status_never_grants_access(monkeypatch):
    recorded = []
    monkeypatch.setattr("app.billing.stripe_checkout.requests.post",
        lambda *a, **kw: recorded.append(kw["json"]) or SimpleNamespace(ok=True))
    billing = StripeBilling(supabase_url="https://db.example", supabase_service_role_key="test")
    billing._sync_subscription(user_id="user", plan_id="reader", customer_id="cus",
        subscription_id="sub", status="incomplete", trial_end=None, period_end=None,
        cancel_at_period_end=False)
    assert recorded[0]["status"] == "expired"


def test_checkout_event_does_not_activate_subscription(monkeypatch):
    requests = []
    monkeypatch.setattr("app.billing.stripe_checkout.requests.post",
        lambda *a, **kw: requests.append(kw["json"]) or SimpleNamespace(ok=True))
    billing = StripeBilling(supabase_url="https://db.example", supabase_service_role_key="test")
    billing.record_verified_event({"id":"evt_checkout","type":"checkout.session.completed",
        "data":{"object":{"id":"cs","subscription":"sub","status":"complete",
        "metadata":{"atlas_user_id":"user","atlas_plan":"reader"}}}})
    assert len(requests) == 1


def test_whish_disabled_until_recipient_configured(monkeypatch):
    monkeypatch.setenv("ATLAS_WHISH_ENABLED", "false")
    r = client().post("/billing/whish/reader/request", json={"email":"a@example.com"})
    assert r.status_code == 503


def test_whish_persists_pending_request_without_granting_access(tmp_path, monkeypatch):
    monkeypatch.setenv("ATLAS_WHISH_ENABLED","true")
    monkeypatch.setenv("ATLAS_WHISH_RECIPIENT","Test merchant")
    monkeypatch.setenv("ATLAS_WHISH_SUPPORT","support@example.com")
    monkeypatch.setenv("ATLAS_WHISH_DB",str(tmp_path/"whish.db"))
    c=client()
    result=c.post("/billing/whish/pro/request",json={"email":"a@example.com"}).json()
    assert result["amount_usd"] == 99
    assert result["status"] == "PENDING_REVIEW"
    assert result["access_granted"] is False
    assert result["automatic_renewal"] is False
    assert c.post("/billing/whish/pro/request",json={"email":"a@example.com"}).json()["reference"] == result["reference"]
    assert c.post("/billing/whish/invalid/request",json={"email":"a@example.com"}).status_code == 404
    assert c.post("/billing/whish/pro/request",json={"email":"invalid"}).status_code == 422


def test_preferences_on_all_pages_and_whish_links():
    assert b"/ui/preferences.js" in dashboard_view().body
    page = subscribe().body
    assert b"/billing/whish/reader" in page and b"/billing/whish/pro" in page
    c = client()
    assert "/ui/preferences.js" in c.get("/billing/whish/reader").text
    script = c.get("/ui/preferences.js")
    assert script.status_code == 200
    assert "atlas-language" in script.text and "atlas-theme" in script.text
