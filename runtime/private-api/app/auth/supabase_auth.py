import os
from contextvars import ContextVar
from dataclasses import dataclass

import jwt
import requests
from fastapi import HTTPException, Request, status

_current_token: ContextVar[str] = ContextVar("atlas_access_token", default="")

@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    email: str | None = None

def supabase_publishable_key() -> str:
    for name in ("SUPABASE_PUBLISHABLE_KEY", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY"):
        value = os.getenv(name, "").strip()
        if value and (name != "SUPABASE_SERVICE_ROLE_KEY" or value.startswith("sb_publishable_")):
            return value
    return ""

def extract_access_token(request: Request) -> str:
    header = request.headers.get("authorization", "")
    scheme, _, raw = header.partition(" ")
    token = raw.strip() if scheme.lower() == "bearer" else ""
    return token or request.cookies.get("atlas_session", "").strip()

def current_access_token() -> str:
    token = _current_token.get().strip()
    if not token:
        raise RuntimeError("No authenticated Supabase user token in request context.")
    return token

def verify_access_token(token: str) -> AuthenticatedUser:
    secret = os.getenv("SUPABASE_JWT_SECRET", "").strip()
    audience = os.getenv("SUPABASE_JWT_AUDIENCE", "authenticated").strip() or "authenticated"
    if secret:
        try:
            payload = jwt.decode(token, secret, algorithms=["HS256"], audience=audience)
            user_id = str(payload.get("sub") or "").strip()
            if not user_id:
                raise jwt.InvalidTokenError("missing subject")
            email = payload.get("email")
            return AuthenticatedUser(user_id=user_id, email=str(email) if email else None)
        except jwt.PyJWTError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session.") from exc

    base_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    public_key = supabase_publishable_key()
    if not base_url or not public_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication unavailable.")
    try:
        response = requests.get(
            f"{base_url}/auth/v1/user",
            headers={"apikey": public_key, "Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication unavailable.") from exc
    if not response.ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session.")
    payload = response.json()
    user_id = str(payload.get("id") or "").strip()
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session.")
    email = payload.get("email")
    return AuthenticatedUser(user_id=user_id, email=str(email) if email else None)

def require_user(request: Request) -> AuthenticatedUser:
    token = extract_access_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    user = verify_access_token(token)
    _current_token.set(token)
    return user
