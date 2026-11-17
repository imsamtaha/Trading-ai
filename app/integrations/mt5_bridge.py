from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

import requests


class RemoteMT5BridgeError(RuntimeError):
    """Raised when remote MT5 telemetry is unavailable or unsafe."""


def _bridge_url() -> str:
    value = os.getenv("ATLAS_MT5_BRIDGE_URL", "").strip().rstrip("/")
    if not value:
        raise RemoteMT5BridgeError("ATLAS_MT5_BRIDGE_URL is not configured.")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RemoteMT5BridgeError("ATLAS_MT5_BRIDGE_URL must be an http(s) URL.")
    return value


def fetch_remote_mt5_telemetry() -> dict[str, Any]:
    """Fetch demo/read-only MT5 telemetry from the Windows bridge.

    This client never submits orders. It accepts only payloads that explicitly
    identify a demo account, READ_ONLY mode, and broker_orders=false.
    """

    base_url = _bridge_url()
    token = os.getenv("ATLAS_MT5_BRIDGE_TOKEN", "").strip()
    timeout = float(os.getenv("ATLAS_MT5_BRIDGE_TIMEOUT_SECONDS", "5"))
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.get(
            f"{base_url}/telemetry",
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError, TypeError) as exc:
        raise RemoteMT5BridgeError(f"Windows MT5 bridge unavailable: {exc}") from exc

    if not isinstance(payload, dict):
        raise RemoteMT5BridgeError("Windows MT5 bridge returned an invalid payload.")

    account = payload.get("account")
    account_type = str(account.get("account_type", "") if isinstance(account, dict) else "").upper()
    mode = str(payload.get("mode", "")).upper()
    broker_orders = payload.get("broker_orders", False)

    if account_type != "DEMO" or mode != "READ_ONLY" or broker_orders is not False:
        raise RemoteMT5BridgeError(
            "Windows MT5 bridge payload is not demo/read-only; telemetry rejected."
        )

    services = payload.setdefault("services", {})
    if isinstance(services, dict):
        services["telemetry_source"] = "WINDOWS_MT5_BRIDGE"
        services["execution_gate"] = "DISABLED"
        services["subscriber_access"] = "READ_ONLY"
    payload["broker_orders"] = False
    payload["mode"] = "READ_ONLY"
    return payload
