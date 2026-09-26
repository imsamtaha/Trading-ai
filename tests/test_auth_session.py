import time

import jwt
import pytest
from fastapi import HTTPException
from starlette.requests import Request


def make_request(token: str | None = None) -> Request:
    headers = []
    if token:
        headers.append((b"authorization", f"Bearer {token}".encode()))
    return Request({"type": "http", "method": "GET", "path": "/", "headers": headers})


def configure(monkeypatch, secret: str = "test-secret-0123456789-0123456789-ab") -> None:
    monkeypatch.setenv("SUPABASE_JWT_SECRET", secret)
    monkeypatch.setenv("SUPABASE_JWT_AUDIENCE", "authenticated")


def test_missing_token_returns_401(monkeypatch):
    configure(monkeypatch)
    from app.auth.supabase_auth import require_user

    with pytest.raises(HTTPException) as exc:
        require_user(make_request())
    assert exc.value.status_code == 401

def test_expired_token_returns_401(monkeypatch):
    configure(monkeypatch)
    from app.auth.supabase_auth import require_user

    token = jwt.encode({"sub": "user-a", "aud": "authenticated", "exp": int(time.time()) - 5}, "test-secret-0123456789-0123456789-ab", algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        require_user(make_request(token))
    assert exc.value.status_code == 401


def test_invalid_token_returns_401(monkeypatch):
    configure(monkeypatch)
    from app.auth.supabase_auth import require_user

    token = jwt.encode({"sub": "user-a", "aud": "authenticated", "exp": int(time.time()) + 60}, "wrong-secret-0123456789-0123456789", algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        require_user(make_request(token))
    assert exc.value.status_code == 401


def test_valid_token_resolves_expected_user(monkeypatch):
    configure(monkeypatch)
    from app.auth.supabase_auth import require_user

    token = jwt.encode({"sub": "user-123", "email": "user@example.com", "aud": "authenticated", "exp": int(time.time()) + 60}, "test-secret-0123456789-0123456789-ab", algorithm="HS256")
    user = require_user(make_request(token))
    assert user.user_id == "user-123"
    assert user.email == "user@example.com"

