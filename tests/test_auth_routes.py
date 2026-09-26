import time

import jwt
from fastapi.testclient import TestClient


def configure(monkeypatch):
    secret = "test-secret-0123456789-0123456789-ab"
    monkeypatch.setenv("SUPABASE_JWT_SECRET", secret)
    monkeypatch.setenv("SUPABASE_JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-public-key")
    return secret


def token(secret: str, sub: str = "user-123") -> str:
    return jwt.encode({"sub": sub, "email": "u@example.com", "aud": "authenticated", "exp": int(time.time()) + 300}, secret, algorithm="HS256")


def test_login_page_offers_google_and_email_otp(monkeypatch):
    configure(monkeypatch)
    from app.main import app
    client = TestClient(app)
    response = client.get("/login")
    assert response.status_code == 200
    assert "Continue with Google" in response.text
    assert "Email code" in response.text


def test_dashboard_redirects_unauthenticated_user(monkeypatch):
    configure(monkeypatch)
    from app.main import app
    client = TestClient(app, follow_redirects=False)
    response = client.get("/dashboard")
    assert response.status_code in {302, 303, 307}
    assert response.headers["location"] == "/login"

def test_authenticated_user_can_open_private_dashboard(monkeypatch):
    secret = configure(monkeypatch)
    from app.main import app
    client = TestClient(app)
    client.cookies.set("atlas_session", token(secret))
    response = client.get("/app/dashboard")
    assert response.status_code == 200
    assert "Private ATLAS Dashboard" in response.text
    assert "user-123" not in response.text


def test_session_endpoint_sets_secure_cookie(monkeypatch):
    secret = configure(monkeypatch)
    from app.main import app
    client = TestClient(app)
    response = client.post("/auth/session", json={"access_token": token(secret)})
    assert response.status_code == 200
    cookie = response.headers.get("set-cookie", "")
    assert "atlas_session=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie


def test_logout_clears_session_cookie(monkeypatch):
    configure(monkeypatch)
    from app.main import app
    client = TestClient(app)
    client.cookies.set("atlas_session", "abc")
    response = client.post("/logout", follow_redirects=False)
    assert response.status_code in {302, 303, 307}
    assert response.headers["location"] == "/"
    assert "atlas_session=" in response.headers.get("set-cookie", "")


def test_auth_labels_have_arabic_translations():
    from app.dashboard.preferences import SCRIPT
    assert "'Continue with Google':'المتابعة باستخدام Google'" in SCRIPT
    assert "'Email code':'رمز البريد الإلكتروني'" in SCRIPT
    assert "'Private ATLAS Dashboard':'لوحة أطلس الخاصة'" in SCRIPT
