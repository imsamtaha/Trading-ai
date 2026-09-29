from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient
from starlette.requests import Request


def configure(monkeypatch):
    secret = "test-secret-key-that-is-long-enough-123456"
    monkeypatch.setenv("SUPABASE_JWT_SECRET", secret)
    monkeypatch.setenv("SUPABASE_JWT_AUDIENCE", "authenticated")
    return secret


def token(secret: str, user_id: str, email: str) -> str:
    return jwt.encode({
        "sub": user_id,
        "email": email,
        "aud": "authenticated",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    }, secret, algorithm="HS256")


def test_memory_repository_defaults_new_user_to_free():
    from app.users.repository import MemoryUserRepository
    repo = MemoryUserRepository()
    profile = repo.get_or_create_profile("user-a", email="a@example.com")
    subscription = repo.get_subscription("user-a")
    assert profile["user_id"] == "user-a"
    assert subscription["plan"] == "FREE"


def test_memory_repository_keeps_users_isolated():
    from app.users.repository import MemoryUserRepository
    repo = MemoryUserRepository()
    repo.get_or_create_profile("user-a", email="a@example.com")
    repo.get_or_create_profile("user-b", email="b@example.com")
    repo.update_user_settings("user-a", {"language": "ar"})
    assert repo.get_user_settings("user-a")["language"] == "ar"
    assert repo.get_user_settings("user-b")["language"] == "en"


def test_settings_route_ignores_client_supplied_user_id(monkeypatch):
    secret = configure(monkeypatch)
    from app.main import app
    import app.users.routes as user_routes
    from app.users.repository import MemoryUserRepository

    repo = MemoryUserRepository()
    monkeypatch.setattr(user_routes, "repository", repo)
    client = TestClient(app)
    client.cookies.set("atlas_session", token(secret, "user-a", "a@example.com"))
    response = client.put("/api/user/settings", json={"user_id": "user-b", "language": "ar"})
    assert response.status_code == 200
    assert repo.get_user_settings("user-a")["language"] == "ar"
    assert repo.get_user_settings("user-b")["language"] == "en"


def test_supabase_repository_uses_user_token_for_rls(monkeypatch):
    import jwt
    from app.auth.supabase_auth import require_user
    from app.users.repository import SupabaseUserRepository

    secret = "test-secret-0123456789-0123456789-ab"
    monkeypatch.setenv("SUPABASE_JWT_SECRET", secret)
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "sb_publishable_test_public_key")
    token_value = jwt.encode({"sub": "user-a", "aud": "authenticated", "exp": 4102444800}, secret, algorithm="HS256")
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": [(b"authorization", f"Bearer {token_value}".encode())]})
    require_user(request)
    repo = SupabaseUserRepository()
    headers = repo._headers()
    assert headers["apikey"] == "sb_publishable_test_public_key"
    assert headers["Authorization"] == f"Bearer {token_value}"
    assert headers["Authorization"] != f"Bearer {headers['apikey']}"
