from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(title="ATLAS Google OAuth Bridge")

BRIDGE_TOKEN = os.getenv("ATLAS_BRIDGE_SERVER_TOKEN", "").strip()
TOKEN_PATH = Path(os.getenv("ATLAS_GOOGLE_TOKEN_PATH", str(Path.home() / ".atlas_google_token.json")))
GOOGLE_CLIENT_ID = os.getenv("ATLAS_GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("ATLAS_GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT_URI = os.getenv("ATLAS_GOOGLE_REDIRECT_URI", "http://127.0.0.1:8001/oauth/google/callback").strip()

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]


class ToolRequest(BaseModel):
    tool: str
    arguments: dict[str, Any] = {}
    approved: bool = False
    caller: str = ""


def _check_auth(authorization: str | None) -> None:
    if not BRIDGE_TOKEN:
        return
    if authorization != f"Bearer {BRIDGE_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")


def _require_google_config() -> None:
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Google OAuth client is not configured")


def _save_token(data: dict[str, Any]) -> None:
    TOKEN_PATH.write_text(json.dumps(data, indent=2))
    try:
        TOKEN_PATH.chmod(0o600)
    except OSError:
        pass


def _load_token() -> dict[str, Any]:
    if not TOKEN_PATH.exists():
        raise HTTPException(status_code=401, detail="Google account is not connected")
    return json.loads(TOKEN_PATH.read_text())


def _refresh_access_token(token: dict[str, Any]) -> str:
    access_token = token.get("access_token")
    if access_token:
        return access_token

    refresh_token = token.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Google OAuth refresh token is missing")

    _require_google_config()
    body = urlencode(
        {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
    ).encode()
    req = Request("https://oauth2.googleapis.com/token", data=body, method="POST")
    with urlopen(req, timeout=20) as response:
        fresh = json.loads(response.read().decode())

    token.update(fresh)
    token["refresh_token"] = refresh_token
    _save_token(token)
    return token["access_token"]


def _google_get(url: str) -> dict[str, Any]:
    token = _load_token()
    access_token = _refresh_access_token(token)
    req = Request(url, headers={"Authorization": f"Bearer {access_token}"})
    with urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode())


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "atlas-google-oauth-bridge",
        "google_configured": bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
        "google_connected": TOKEN_PATH.exists(),
    }


@app.get("/oauth/google/start")
def google_oauth_start() -> dict[str, str]:
    _require_google_config()
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    return {"authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)}


@app.get("/oauth/google/callback")
def google_oauth_callback(code: str) -> dict[str, Any]:
    _require_google_config()
    body = urlencode(
        {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }
    ).encode()
    req = Request("https://oauth2.googleapis.com/token", data=body, method="POST")
    with urlopen(req, timeout=20) as response:
        token = json.loads(response.read().decode())
    _save_token(token)
    return {"status": "connected", "token_path": str(TOKEN_PATH)}


@app.post("/execute")
def execute(payload: ToolRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_auth(authorization)

    if payload.tool.endswith(".write") and not payload.approved:
        return {
            "status": "APPROVAL_REQUIRED",
            "tool": payload.tool,
            "message": "Explicit approval is required before external writes.",
        }

    if payload.tool == "gmail.read":
        query = payload.arguments.get("query", "newer_than:7d -in:spam -in:trash")
        max_results = int(payload.arguments.get("max_results", 10))
        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages?" + urlencode(
            {"q": query, "maxResults": max_results}
        )
        return _google_get(url)

    if payload.tool == "calendar.read":
        params = {
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": int(payload.arguments.get("max_results", 20)),
        }
        if payload.arguments.get("time_min"):
            params["timeMin"] = payload.arguments["time_min"]
        if payload.arguments.get("time_max"):
            params["timeMax"] = payload.arguments["time_max"]
        url = "https://www.googleapis.com/calendar/v3/calendars/primary/events?" + urlencode(params)
        return _google_get(url)

    raise HTTPException(status_code=400, detail=f"Tool not implemented: {payload.tool}")
