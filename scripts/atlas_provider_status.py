"""Authenticated, account-scoped read-only status for the Tiger Shield Site."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from hmac import compare_digest
import math
import os
from threading import Lock
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Response

from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError
from app.integrations.ctrader_demo import read_demo_account, read_live_account

app = FastAPI(title="ATLAS read-only provider status", docs_url=None, redoc_url=None, openapi_url=None)
_mt5_session = Lock()
_account_modes = {"DEMO": 0, "REAL": 2}


def _require_reader(
    authorization: str | None, response: Response,
    *, token_name: str = "ATLAS_PROVIDER_STATUS_TOKEN",
) -> None:
    response.headers["Cache-Control"] = "private, no-store"
    expected = os.getenv(token_name, "").strip()
    if not expected:
        raise HTTPException(503, "Provider status is not configured.")
    if not compare_digest((authorization or "").encode(), f"Bearer {expected}".encode()):
        raise HTTPException(401, "Unauthorized status request.")


def _snapshot(
    *, mode: str, as_of: str, balance: object, currency: object, broker: object,
) -> dict[str, Any]:
    try:
        amount = float(balance)
        if not math.isfinite(amount):
            amount = None
    except (TypeError, ValueError, OverflowError):
        amount = None
    return {
        "status": "CONNECTED",
        "environment": mode,
        "access": "READ_ONLY",
        "brokerOrders": False,
        "asOf": as_of,
        "balance": amount,
        "currency": currency,
        "broker": broker,
    }


@app.get("/status/mt5")
def mt5_status(response: Response, authorization: str | None = Header(default=None)):
    _require_reader(authorization, response)
    mode = os.getenv("ATLAS_MT5_STATUS_ACCOUNT_TYPE", "DEMO").strip().upper()
    if mode not in _account_modes or os.getenv("ATLAS_LIVE_TRADING", "false").lower() != "false":
        raise HTTPException(503, "Read-only MT5 status is unavailable.")
    try:
        config = MT5Config.from_env()
        if not config.login or not config.server or not config.terminal_path:
            raise ValueError("A dedicated, identified terminal is required.")
        with _mt5_session:
            # Read the independently signed-in terminal. This service never switches accounts.
            broker = MT5Broker(replace(config, dry_run=True, use_active_session=True))
            try:
                account = broker.connect()
                if (account["login"], account["server"], account["trade_mode"]) != (
                    config.login, config.server, _account_modes[mode],
                ):
                    raise MT5ExecutionError("Wrong MT5 account is active.")
                return _snapshot(
                    mode=mode, as_of=datetime.now(timezone.utc).isoformat(),
                    balance=account["balance"], currency=account["currency"], broker=account["server"],
                )
            finally:
                if broker.connected:
                    broker.disconnect()
    except (MT5ExecutionError, KeyError, TypeError, ValueError):
        raise HTTPException(503, "Read-only MT5 status is unavailable.") from None


@app.get("/status/ctrader")
@app.get("/status/ctrader/demo")
def ctrader_status(response: Response, authorization: str | None = Header(default=None)):
    _require_reader(authorization, response)
    if os.getenv("ATLAS_LIVE_TRADING", "false").strip().lower() != "false":
        raise HTTPException(503, "Read-only cTrader status is unavailable.")
    account = read_demo_account(require_selected=False)
    if (account.get("status"), account.get("environment"), account.get("access")) != (
        "CONNECTED", "DEMO", "VIEW_ONLY",
    ):
        raise HTTPException(503, "Read-only cTrader status is unavailable.")
    return _snapshot(
        mode="DEMO", as_of=account["as_of"], balance=account.get("balance"),
        currency=account.get("currency"), broker=account.get("broker"),
    )


@app.get("/status/ctrader/live")
def ctrader_live_status(response: Response, authorization: str | None = Header(default=None)):
    # Dedicated secret: a demo or MT5 status token never grants LIVE account visibility.
    _require_reader(authorization, response, token_name="ATLAS_PROVIDER_LIVE_STATUS_TOKEN")
    if os.getenv("ATLAS_LIVE_TRADING", "false").strip().lower() != "false":
        raise HTTPException(503, "Read-only cTrader LIVE status is unavailable.")
    account = read_live_account()
    if (account.get("status"), account.get("environment"), account.get("access")) != (
        "CONNECTED", "LIVE", "VIEW_ONLY",
    ):
        raise HTTPException(503, "Read-only cTrader LIVE status is unavailable.")
    return _snapshot(
        mode="LIVE", as_of=account["as_of"], balance=account.get("balance"),
        currency=account.get("currency"), broker=account.get("broker"),
    )
