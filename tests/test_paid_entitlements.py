from datetime import datetime, timedelta, timezone

from app.billing.entitlements import paid_access
from app.users.repository import SupabaseUserRepository


def test_paid_access_requires_verified_active_unexpired_whish():
    future = (datetime.now(timezone.utc) + timedelta(days=20)).isoformat()
    base = {"plan": "STARTER", "status": "ACTIVE", "billing_reference": "ATLAS-VERIFIED", "expires_at": future}
    assert paid_access(base)
    for changed in (
        {"plan": "FREE"}, {"status": "PENDING_REVIEW"},
        {"billing_reference": None}, {"expires_at": None},
        {"expires_at": "2000-01-01T00:00:00+00:00"},
    ):
        assert not paid_access({**base, **changed})


def test_profile_creation_never_writes_subscription_as_customer():
    repo = SupabaseUserRepository.__new__(SupabaseUserRepository)
    writes = []
    repo._select_one = lambda table, user_id: None
    repo._upsert = lambda table, row: writes.append(table) or row
    repo.get_or_create_profile("user-a", "test@example.com")
    assert "atlas_user_profiles" in writes
    assert "atlas_user_subscriptions" not in writes

def test_assistant_is_denied_until_owner_verifies_paid_subscription(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.users import routes
    from app.auth.supabase_auth import AuthenticatedUser
    from app.users.repository import MemoryUserRepository

    repo = MemoryUserRepository()
    monkeypatch.setattr(routes, "repository", repo)
    monkeypatch.setattr(routes, "require_user", lambda request: AuthenticatedUser("user-a"))
    monkeypatch.setattr(routes, "answer_assistant", lambda user_id, message: "safe answer")
    client = TestClient(app)
    assert client.post("/api/user/assistant", json={"message": "hello"}).status_code == 403
    repo.get_or_create_profile("user-a")
    repo.subscriptions["user-a"] = {"plan": "PRO", "status": "ACTIVE", "billing_reference": "ATLAS-PAID",
                                    "expires_at": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()}
    assert client.post("/api/user/assistant", json={"message": "hello"}).json() == {"message": "safe answer"}

def test_unpaid_user_cannot_start_demo_intelligence_or_read_private_briefing(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.users import routes as user_routes
    from app.demo_executive import routes as demo_routes
    from app.auth.supabase_auth import AuthenticatedUser
    from app.users.repository import MemoryUserRepository

    repo = MemoryUserRepository()
    monkeypatch.setattr(user_routes, "repository", repo)
    monkeypatch.setattr(user_routes, "require_user", lambda request: AuthenticatedUser("user-a"))
    monkeypatch.setattr(demo_routes, "require_user", lambda request: AuthenticatedUser("user-a"))
    client = TestClient(app)
    assert client.get("/api/user/market-briefing").status_code == 403
    assert client.post("/api/demo-executive/start").status_code == 403

def test_dashboard_reports_entitlement_without_granting_free_intelligence(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.users import routes
    from app.auth.supabase_auth import AuthenticatedUser
    from app.users.repository import MemoryUserRepository

    repo = MemoryUserRepository()
    monkeypatch.setattr(routes, "repository", repo)
    monkeypatch.setattr(routes, "require_user", lambda request: AuthenticatedUser("user-a"))
    response = TestClient(app).get("/api/user/dashboard")
    assert response.status_code == 200
    assert response.json()["features"]["trading_intelligence"] is False
    assert response.json()["features"]["demo_executive"] is False

def test_whish_request_is_bound_to_signed_in_email(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.billing import whish
    from app.auth.supabase_auth import AuthenticatedUser

    monkeypatch.setenv("ATLAS_WHISH_ENABLED", "true")
    monkeypatch.setenv("ATLAS_WHISH_RECIPIENT", "Test merchant")
    monkeypatch.setenv("ATLAS_WHISH_SUPPORT", "support@example.com")
    monkeypatch.setenv("ATLAS_WHISH_DB", str(tmp_path / "whish.db"))
    monkeypatch.setattr(whish, "require_user", lambda request: AuthenticatedUser("user-a", "actual@example.com"), raising=False)
    client = TestClient(app)
    assert client.post("/billing/whish/starter/request", json={"email": "other@example.com"}).status_code == 403
    result = client.post("/billing/whish/starter/request", json={"email": "actual@example.com"})
    assert result.status_code == 200
    assert result.json()["access_granted"] is False

def test_guest_market_preview_has_no_account_or_mt5_connection(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.users import routes
    from app.mt5_demo import routes as demo_routes

    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    monkeypatch.setattr(routes, "get_candles", lambda symbol, interval, limit:
                        {"symbol": symbol, "interval": interval, "count": 1,
                         "candles": [{"time": 1, "open": 1, "high": 2, "low": 1, "close": 2}]})
    monkeypatch.setattr(demo_routes, "_service", lambda: (_ for _ in ()).throw(AssertionError("MT5 called")))
    client = TestClient(app)
    response = client.get("/api/market-preview?symbol=XAUUSD&interval=1h")
    assert response.status_code == 200
    assert response.json()["candles"][0]["close"] == 2
    assert "account" not in response.json()



def test_whish_owner_review_approves_only_pending_request(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.billing import whish
    from app.auth.supabase_auth import AuthenticatedUser

    monkeypatch.setenv("ATLAS_WHISH_ENABLED", "true")
    monkeypatch.setenv("ATLAS_WHISH_RECIPIENT", "Test merchant")
    monkeypatch.setenv("ATLAS_WHISH_SUPPORT", "support@example.com")
    monkeypatch.setenv("ATLAS_WHISH_DB", str(tmp_path / "whish.db"))
    monkeypatch.setattr(whish, "require_user", lambda request: AuthenticatedUser("customer-1", "buyer@example.com"))
    client = TestClient(app)
    reference = client.post("/billing/whish/starter/request", json={"email": "buyer@example.com"}).json()["reference"]
    assert client.get("/billing/whish/admin/requests").status_code == 403
    assert client.post(f"/billing/whish/admin/{reference}/approve").status_code == 403
    monkeypatch.setattr(whish, "require_user", lambda request: AuthenticatedUser("admin-1", "imsamtaha.ai@gmail.com"))
    approvals = []
    monkeypatch.setattr(whish, "_activate_subscription", lambda user_id, plan_id, ref: approvals.append((user_id, plan_id, ref)))
    assert client.get("/billing/whish/admin/requests").json()["requests"][0]["reference"] == reference
    approved = client.post(f"/billing/whish/admin/{reference}/approve")
    assert approved.status_code == 200
    assert approvals == [("customer-1", "starter", reference)]
    assert client.post(f"/billing/whish/admin/{reference}/approve").status_code == 409



def test_whish_notification_targets_owner_when_mail_is_configured(monkeypatch):
    from app.billing import whish
    sent = []
    class FakeSMTP:
        def __init__(self, host, port, timeout): assert host == "smtp.example.com"
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def starttls(self): pass
        def login(self, username, password): pass
        def send_message(self, message): sent.append(message)
    for key, value in {"ATLAS_SMTP_HOST": "smtp.example.com", "ATLAS_SMTP_FROM": "atlas@example.com",
                       "ATLAS_SMTP_USER": "atlas", "ATLAS_SMTP_PASSWORD": "test-only"}.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(whish.smtplib, "SMTP", FakeSMTP)
    assert whish._notify_admin("ATLAS-ABC", "buyer@example.com", "starter")
    assert sent[0]["To"] == "imsamtaha.ai@gmail.com"
    assert "buyer@example.com" in sent[0].get_content()


def test_owner_account_gets_dashboard_owner_role_without_changing_customer_access(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.users import routes
    from app.auth.supabase_auth import AuthenticatedUser
    from app.users.repository import MemoryUserRepository

    repo = MemoryUserRepository()
    monkeypatch.setenv("ATLAS_OWNER_EMAIL", "owner@example.com")
    monkeypatch.setattr(routes, "repository", repo)
    monkeypatch.setattr(routes, "require_user", lambda request: AuthenticatedUser("owner-1", "owner@example.com"))
    owner = TestClient(app).get("/api/user/dashboard")
    assert owner.status_code == 200
    assert owner.json()["user"]["role"] == "OWNER"
    assert owner.json()["features"]["trading_intelligence"] is True

    monkeypatch.setattr(routes, "require_user", lambda request: AuthenticatedUser("customer-1", "customer@example.com"))
    customer = TestClient(app).get("/api/user/dashboard")
    assert customer.json()["user"]["role"] == "CUSTOMER"
    assert customer.json()["features"]["trading_intelligence"] is False
