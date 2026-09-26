from __future__ import annotations

import os
from dataclasses import dataclass

import jwt
from fastapi import HTTPException, Request, status


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    email: str | None = None


def verify_access_token(token: str) -> AuthenticatedUser:
    secret = os.getenv("SUPABASE_JWT_SECRET", "").strip()
    audience = os.getenv("SUPABASE_JWT_AUDIENCE", "authenticated").strip() or "authenticated"
    if not secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication unavailable.")
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"], audience=audience)
        user_id = str(payload.get("sub") or "").strip()
        if not user_id:
            raise jwt.InvalidTokenError("missing subject")
        email = payload.get("email")
        return AuthenticatedUser(user_id=user_id, email=str(email) if email else None)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session.") from exc


def require_user(request: Request) -> AuthenticatedUser:
    header = request.headers.get("authorization", "")
    scheme, _, header_token = header.partition(" ")
    token = header_token.strip() if scheme.lower() == "bearer" else ""
    if not token:
        token = request.cookies.get("atlas_session", "").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return verify_access_token(token)
