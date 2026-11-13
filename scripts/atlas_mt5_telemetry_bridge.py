from __future__ import annotations

import os
import hmac
from typing import Any

from fastapi import FastAPI, Header, HTTPException

from app.dashboard.api import atlas_dashboard_state


app = FastAPI(
    title="ATLAS MT5 Telemetry Bridge",
    description="Demo-only, read-only Windows MT5 telemetry for ATLAS clients.",
    version="1.0.0",
)


def _expected_token() -> str:
    return os.getenv("ATLAS_MT5_BRIDGE_TOKEN", "").strip()


def _require_token(authorization: str | None) -> None:
    expected = _expected_token()
    if not expected:
        raise HTTPException(status_code=503, detail="Bridge token is not configured.")
    if not hmac.compare_digest(authorization or "", f"Bearer {expected}"):
        raise HTTPException(status_code=401, detail="Unauthorized telemetry request.")


def _assert_demo_read_only(payload: dict[str, Any]) -> dict[str, Any]:
    account = payload.get("account")
    account_type = str(account.get("account_type", "") if isinstance(account, dict) else "").upper()
    mode = str(payload.get("mode", "")).upper()

    if os.getenv("ATLAS_LIVE_TRADING", "false").lower() != "false":
        raise HTTPException(status_code=503, detail="Bridge refuses live-execution configuration.")
    if account_type != "DEMO":
        raise HTTPException(status_code=503, detail="Bridge requires an MT5 demo account.")
    if mode != "READ_ONLY":
        raise HTTPException(status_code=503, detail="Bridge requires READ_ONLY dashboard state.")

    services = payload.setdefault("services", {})
    if isinstance(services, dict):
        services["execution_gate"] = "DISABLED"
        services["subscriber_access"] = "READ_ONLY"
        services["telemetry_source"] = "WINDOWS_MT5_BRIDGE"

    payload["mode"] = "READ_ONLY"
    payload["broker_orders"] = False
    payload["remote_bridge"] = True
    return payload


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "atlas-mt5-telemetry-bridge",
        "mode": "READ_ONLY",
        "broker_orders": False,
    }


@app.get("/telemetry")
def telemetry(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _require_token(authorization)

    # Force the Windows process into demo/read-only expectations before reading MT5.
    os.environ["ATLAS_LIVE_TRADING"] = "false"
    os.environ["ATLAS_DASHBOARD_ONLY"] = "true"
    os.environ["MT5_REQUIRE_DEMO"] = "true"

    remote_url = os.environ.pop("ATLAS_MT5_BRIDGE_URL", None)
    try:
        payload = atlas_dashboard_state()
    finally:
        if remote_url is not None:
            os.environ["ATLAS_MT5_BRIDGE_URL"] = remote_url
    return _assert_demo_read_only(payload)


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("ATLAS_MT5_BRIDGE_HOST", "0.0.0.0")
    port = int(os.getenv("ATLAS_MT5_BRIDGE_PORT", "8765"))
    uvicorn.run(app, host=host, port=port)
