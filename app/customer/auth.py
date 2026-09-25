from __future__ import annotations

import os
import requests


class CustomerAuthError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 401):
        super().__init__(message)
        self.status_code = status_code


def verify_supabase_access_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise CustomerAuthError("Bearer authentication is required.", status_code=401)
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise CustomerAuthError("Bearer authentication is required.", status_code=401)
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    public_key = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
    if not url or not public_key:
        raise CustomerAuthError("Supabase customer authentication is not configured.", status_code=503)
    try:
        response = requests.get(
            f"{url}/auth/v1/user",
            headers={"Authorization": f"Bearer {token}", "apikey": public_key},
            timeout=5,
        )
    except requests.RequestException as exc:
        raise CustomerAuthError("Customer authentication service is unavailable.", status_code=503) from exc
    if response.status_code != 200:
        raise CustomerAuthError("Customer authentication failed.", status_code=401)
    payload = response.json()
    subject = str(payload.get("id") or "").strip()
    if not subject:
        raise CustomerAuthError("Authenticated user identity is missing.", status_code=401)
    return subject
