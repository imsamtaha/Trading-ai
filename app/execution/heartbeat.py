from __future__ import annotations

import json
import logging
import os
import socket
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from app.execution.mt5 import MT5Broker, MT5ExecutionError


logger = logging.getLogger(__name__)


class AtlasHeartbeat:
    """Publishes MT5 connectivity and execution events to Supabase REST."""

    def __init__(self, broker: MT5Broker | None = None):
        self.broker = broker or MT5Broker()
        self.url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv(
            "SUPABASE_SERVICE_ROLE_KEY", ""
        )
        self.connection_id: str | None = None
        self.last_error: str | None = None

        if not self.url:
            self.last_error = "Supabase audit disabled: SUPABASE_URL is not configured."
            logger.warning(self.last_error)
        elif not self.key:
            self.last_error = (
                "Supabase audit disabled: SUPABASE_SECRET_KEY or "
                "SUPABASE_SERVICE_ROLE_KEY is not configured."
            )
            logger.warning(self.last_error)

    def _request(self, path: str, method: str, payload: dict[str, Any] | None = None) -> Any:
        if not self.url or not self.key:
            return None

        body = json.dumps(payload).encode() if payload is not None else None
        headers = {
            "apikey": self.key,
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        # New Supabase sb_secret_* keys are opaque API keys rather than JWTs.
        # Send them only via apikey; legacy service_role JWTs still use Bearer.
        if not self.key.startswith("sb_secret_"):
            headers["Authorization"] = f"Bearer {self.key}"

        request = urllib.request.Request(
            f"{self.url}/rest/v1/{path}",
            data=body,
            method=method,
            headers=headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                raw = response.read()
                self.last_error = None
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            self.last_error = (
                f"Supabase audit request failed: HTTP {exc.code} {exc.reason}; "
                f"method={method} path={path}"
            )
            logger.warning(self.last_error)
            return None
        except (urllib.error.URLError, TimeoutError) as exc:
            self.last_error = (
                f"Supabase audit request failed: {exc}; method={method} path={path}"
            )
            logger.warning(self.last_error)
            return None

    def publish_connection(self, account: dict[str, Any], status: str = "connected") -> None:
        payload = {
            "environment": os.getenv("ATLAS_ENVIRONMENT", "demo"),
            "broker": "MetaTrader 5",
            "server": account.get("server"),
            "mt5_login": account.get("login"),
            "terminal_host": socket.gethostname(),
            "status": status,
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if self.connection_id:
            self._request(
                f"atlas_mt5_connections?id=eq.{self.connection_id}",
                "PATCH",
                payload,
            )
            return

        rows = self._request("atlas_mt5_connections", "POST", payload)
        if isinstance(rows, list) and rows:
            self.connection_id = rows[0].get("id")

    def heartbeat(self) -> dict[str, Any]:
        try:
            account = self.broker.connect()
            self.publish_connection(account, "connected")
            return {"status": "connected", "account": account}
        except MT5ExecutionError as exc:
            self.publish_connection({"server": None, "login": None}, "error")
            return {"status": "error", "error": str(exc)}

    def publish_event(self, event: dict[str, Any]) -> None:
        payload = dict(event)
        payload["connection_id"] = self.connection_id
        self._request("atlas_execution_events", "POST", payload)
