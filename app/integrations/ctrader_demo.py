"""View-only connection to the cTrader Open API demo environment."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from websockets.exceptions import WebSocketException
from websockets.sync.client import ClientConnection, connect

from app.execution.provider_mode import ctrader_selected


DEMO_ENDPOINT = "wss://demo.ctraderapi.com:5036"
# Documented JSON payload types. The owner surface only uses these requests.
APPLICATION_AUTH = (2100, 2101)
ACCOUNTS_BY_ACCESS_TOKEN = (2149, 2150)
ACCOUNT_AUTH = (2102, 2103)
TRADER = (2121, 2122)
ASSET_LIST = (2112, 2113)
HEARTBEAT = 51
ERROR_RESPONSES = {50, 2142, 2147, 2148, 2164}


class DemoConnectionError(RuntimeError):
    """A sanitized status reason for the private owner dashboard."""


def _receive(session: ClientConnection, timeout: float) -> dict[str, Any]:
    try:
        message = json.loads(session.recv(timeout=max(0, timeout)))
    except TimeoutError:
        raise DemoConnectionError("PROVIDER_TIMEOUT") from None
    except (OSError, ValueError, TypeError, WebSocketException):
        raise DemoConnectionError("INVALID_OR_UNAVAILABLE_PROVIDER_RESPONSE") from None
    if not isinstance(message, dict) or type(message.get("payloadType")) is not int:
        raise DemoConnectionError("INVALID_PROVIDER_RESPONSE")
    if message["payloadType"] in ERROR_RESPONSES:
        raise DemoConnectionError("PROVIDER_REJECTED_REQUEST")
    return message


def _send(session: ClientConnection, message: dict[str, Any]) -> None:
    try:
        session.send(json.dumps(message))
    except (OSError, WebSocketException):
        raise DemoConnectionError("PROVIDER_CONNECTION_FAILED") from None


def _request(
    session: ClientConnection,
    message_types: tuple[int, int],
    payload: dict[str, Any],
    deadline: float,
    *,
    on_event: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    request_type, response_type = message_types
    message_id = uuid4().hex
    _send(session, {
        "clientMsgId": message_id,
        "payloadType": request_type,
        "payload": payload,
    })
    while (remaining := deadline - time.monotonic()) > 0:
        message = _receive(session, remaining)
        if message.get("payloadType") == response_type and message.get("clientMsgId") == message_id:
            result = message.get("payload", {})
            if isinstance(result, dict):
                return result
            raise DemoConnectionError("INVALID_PROVIDER_RESPONSE")
        if on_event:
            on_event(message)
    raise DemoConnectionError("PROVIDER_TIMEOUT")


def _account_id(accounts: dict[str, Any], login: str) -> int:
    scope = accounts.get("permissionScope")
    if scope != "SCOPE_VIEW" and not (type(scope) is int and scope == 0):
        raise DemoConnectionError("VIEW_ONLY_AUTHORIZATION_REQUIRED")
    rows = accounts.get("ctidTraderAccount", [])
    if not isinstance(rows, list):
        raise DemoConnectionError("INVALID_PROVIDER_RESPONSE")
    candidates = [
        row.get("ctidTraderAccountId") for row in rows
        if isinstance(row, dict)
        and row.get("isLive", False) is False
        and str(row.get("traderLogin", "")) == login
    ]
    if len(candidates) != 1:
        raise DemoConnectionError("DEMO_LOGIN_NOT_UNIQUE_OR_NOT_AUTHORIZED")
    account_id = candidates[0]
    if isinstance(account_id, bool) or not str(account_id).isascii() or not str(account_id).isdecimal():
        raise DemoConnectionError("INVALID_PROVIDER_RESPONSE")
    account_id = int(account_id)
    if not 0 < account_id < 2**64:
        raise DemoConnectionError("INVALID_PROVIDER_RESPONSE")
    return account_id


@dataclass(frozen=True, repr=False)
class DemoCredentials:
    client_id: str
    client_secret: str
    access_token: str
    login: str

    @classmethod
    def from_env(cls) -> "DemoCredentials":
        values = [os.getenv("ATLAS_CTRADER_" + name, "").strip()
                  for name in ("CLIENT_ID", "CLIENT_SECRET", "ACCESS_TOKEN", "DEMO_LOGIN")]
        login = values[-1]
        if not all(values) or not login.isascii() or not login.isdecimal():
            raise DemoConnectionError("DEMO_LOGIN_AND_VIEW_ONLY_CREDENTIALS_REQUIRED")
        return cls(*values)


@contextmanager
def demo_session(credentials: DemoCredentials) -> Iterator[tuple[ClientConnection, int]]:
    """Open a demo-only session and verify the granted scope before account auth."""
    try:
        with connect(DEMO_ENDPOINT, open_timeout=4, close_timeout=1, max_size=4 * 2**20) as session:
            deadline = time.monotonic() + 8
            _request(session, APPLICATION_AUTH, {
                "clientId": credentials.client_id, "clientSecret": credentials.client_secret,
            }, deadline)
            accounts = _request(session, ACCOUNTS_BY_ACCESS_TOKEN, {
                "accessToken": credentials.access_token,
            }, deadline)
            account_id = _account_id(accounts, credentials.login)
            authorization = _request(session, ACCOUNT_AUTH, {
                "ctidTraderAccountId": account_id, "accessToken": credentials.access_token,
            }, deadline)
            _verify_account(authorization, account_id)
            yield session, account_id
    except (OSError, ValueError, TypeError, WebSocketException):
        raise DemoConnectionError("PROVIDER_CONNECTION_FAILED") from None


def _verify_account(payload: dict[str, Any], account_id: int) -> None:
    if str(payload.get("ctidTraderAccountId")) != str(account_id):
        raise DemoConnectionError("ACCOUNT_ID_MISMATCH")


def _account_snapshot(credentials: DemoCredentials) -> dict[str, Any]:
    with demo_session(credentials) as (session, account_id):
        deadline = time.monotonic() + 8
        account_request = {"ctidTraderAccountId": account_id}
        trader_result = _request(session, TRADER, account_request, deadline)
        trader = trader_result.get("trader")
        _verify_account(trader_result, account_id)
        if not isinstance(trader, dict):
            raise DemoConnectionError("INVALID_PROVIDER_RESPONSE")
        _verify_account(trader, account_id)
        assets = _request(session, ASSET_LIST, account_request, deadline)
        _verify_account(assets, account_id)

    deposit_asset = trader.get("depositAssetId")
    asset_rows = assets.get("asset", [])
    if not isinstance(asset_rows, list):
        raise DemoConnectionError("INVALID_PROVIDER_RESPONSE")
    currency = next((
        asset.get("name") for asset in asset_rows
        if isinstance(asset, dict) and deposit_asset is not None
        and str(asset.get("assetId")) == str(deposit_asset)
        and isinstance(asset.get("name"), str)
    ), None)
    raw_balance = trader.get("balance")
    digits = trader.get("moneyDigits")
    balance = None
    if type(digits) is int and 0 <= digits <= 18 and len(str(raw_balance)) <= 20:
        if str(raw_balance).removeprefix("-").isascii() and str(raw_balance).removeprefix("-").isdecimal():
            balance = format(Decimal(str(raw_balance)).scaleb(-digits), "f")
    broker = trader.get("brokerName")
    return {
        "status": "CONNECTED",
        "environment": "DEMO",
        "access": "VIEW_ONLY",
        "login_masked": f"***{credentials.login[-4:]}",
        "broker": broker[:100] if isinstance(broker, str) else None,
        "balance": balance,
        "currency": currency[:16] if currency else None,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


def read_demo_account() -> dict[str, Any]:
    if not ctrader_selected():
        return {"status": "INACTIVE"}
    try:
        credentials = DemoCredentials.from_env()
    except DemoConnectionError as exc:
        return {"status": "NOT_CONFIGURED", "reason": str(exc)}
    try:
        return _account_snapshot(credentials)
    except DemoConnectionError as exc:
        return {"status": "UNAVAILABLE", "reason": str(exc)}
