"""Authorize a cTrader demo account with the accounts (view-only) scope."""

from __future__ import annotations

import getpass
import os
import secrets
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import parse_qs, urlencode, urlsplit

import requests
from dotenv import dotenv_values, set_key

from app.integrations.ctrader_demo import DemoConnectionError, DemoCredentials, demo_session

AUTHORIZE = "https://id.ctrader.com/my/settings/openapi/grantingaccess/"
TOKEN_ENDPOINT = "https://openapi.ctrader.com/apps/token"
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


def redirect_base(redirect: str):
    parsed = urlsplit(redirect)
    if (
        not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or (
            parsed.scheme != "https"
            and not (parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "::1", "localhost"})
        )
    ):
        raise ValueError("Use an HTTPS or local loopback redirect URI registered with cTrader.")
    return parsed


def callback_code(registered: str, callback: str) -> str:
    expected, actual = redirect_base(registered), redirect_base(callback)
    query = parse_qs(actual.query, keep_blank_values=True)
    codes = query.pop("code", [])
    if (
        (expected.scheme, expected.netloc, expected.path) != (actual.scheme, actual.netloc, actual.path)
        or query != parse_qs(expected.query, keep_blank_values=True)
        or len(codes) != 1
        or not codes[0]
        or len(codes[0]) > 4096
    ):
        raise ValueError("The callback must match your registered redirect URI and contain one authorization code.")
    return codes[0]


def exchange_code(client_id: str, client_secret: str, redirect: str, code: str) -> str:
    access_token = None
    try:
        response = requests.get(
            TOKEN_ENDPOINT,
            params={
                "grant_type": "authorization_code", "client_id": client_id,
                "client_secret": client_secret, "redirect_uri": redirect, "code": code,
            },
            timeout=10, allow_redirects=False,
        )
        if response.status_code == 200 and len(response.content) <= 65536:
            payload = response.json()
            if isinstance(payload, dict) and not payload.get("errorCode"):
                access_token = payload.get("accessToken")
    except (requests.RequestException, ValueError):
        pass
    if not isinstance(access_token, str) or not access_token or len(access_token) > 8192:
        raise DemoConnectionError("TOKEN_EXCHANGE_FAILED: create a fresh cTrader authorization code.")
    return access_token


def save_env(path: Path, settings: dict[str, str]) -> None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("The project .env must be a regular file.")
    original = path.read_bytes() if path.exists() else b""
    with NamedTemporaryFile(dir=path.parent, prefix=".env.ctrader-", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(original)
    try:
        for key, value in settings.items():
            set_key(temporary, key, value)
        current = path.read_bytes() if path.exists() else b""
        if path.is_symlink() or current != original:
            raise ValueError("The project .env changed during setup. Run authorization again.")
        os.chmod(temporary, 0o600)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    if not sys.stdin.isatty():
        print("Run this setup interactively from a private terminal.", file=sys.stderr)
        return 2
    try:
        if ENV_PATH.is_symlink() or (ENV_PATH.exists() and not ENV_PATH.is_file()):
            raise ValueError("The project .env must be a regular file.")
        existing = dotenv_values(ENV_PATH, interpolate=False)
        def setting(key: str) -> str:
            return (os.getenv(key) or existing.get(key) or "").strip()

        client_id = setting("ATLAS_CTRADER_CLIENT_ID") or input("Approved cTrader Open API client ID: ").strip()
        client_secret = setting("ATLAS_CTRADER_CLIENT_SECRET") or getpass.getpass("cTrader Open API client secret: ").strip()
        login = setting("ATLAS_CTRADER_DEMO_LOGIN") or input("cTrader demo account number: ").strip()
        redirect = setting("ATLAS_CTRADER_REDIRECT_URI") or input("Exact redirect URI registered in the cTrader app: ").strip()
        if not (client_id and client_secret and login.isascii() and login.isdecimal()):
            raise ValueError("Enter an app ID, app secret, and numeric demo login.")
        redirect_base(redirect)
        if "code" in parse_qs(urlsplit(redirect).query, keep_blank_values=True):
            raise ValueError("Enter the registered redirect URI without an authorization code.")
        query = urlencode({"client_id": client_id, "redirect_uri": redirect, "scope": "accounts", "product": "web"})
        print(f"Open this URL in your own browser and select the demo account:\n{AUTHORIZE}?{query}")
        callback = getpass.getpass("Paste the full redirected URL here (hidden): ").strip()
        code = callback_code(redirect, callback)
        token = exchange_code(client_id, client_secret, redirect, code)
        with demo_session(DemoCredentials(client_id, client_secret, token, login)):
            pass
        save_env(ENV_PATH, {
            "ATLAS_BROKER_PROVIDER": "ctrader",
            "ATLAS_MT5_CONNECTIONS_PAUSED": "true",
            "ATLAS_LIVE_TRADING": "false",
            "ATLAS_DASHBOARD_ONLY": "true",
            "ATLAS_CTRADER_CLIENT_ID": client_id,
            "ATLAS_CTRADER_CLIENT_SECRET": client_secret,
            "ATLAS_CTRADER_DEMO_LOGIN": login,
            "ATLAS_CTRADER_REDIRECT_URI": redirect,
            "ATLAS_CTRADER_ACCESS_TOKEN": token,
            "ATLAS_CTRADER_MARKET_TOKEN": setting("ATLAS_CTRADER_MARKET_TOKEN") or secrets.token_urlsafe(32),
        })
        print(f"Verified demo account ***{login[-4:]} with view-only access. Saved to the project .env.")
        return 0
    except (ValueError, DemoConnectionError) as exc:
        print(str(exc), file=sys.stderr)
    except (OSError, EOFError, KeyboardInterrupt):
        print("Setup cancelled or private configuration could not be saved.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
