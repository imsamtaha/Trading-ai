"""View-only connection to the cTrader Open API demo environment."""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Iterator
from uuid import uuid4

from websockets.exceptions import WebSocketException
from websockets.sync.client import ClientConnection, connect

from app.execution.provider_mode import ctrader_selected


DEMO_ENDPOINT = "wss://demo.ctraderapi.com:5036"
# Documented JSON payload types for view-only access.
APPLICATION_AUTH = (2100, 2101)
ACCOUNTS_BY_ACCESS_TOKEN = (2149, 2150)
ACCOUNT_AUTH = (2102, 2103)
TRADER = (2121, 2122)
ASSET_LIST = (2112, 2113)
ERROR_RESPONSES = {50, 2142, 2147, 2148, 2164}


class DemoConnectionError(RuntimeError):
    """A sanitized status reason for the private owner dashboard."""


def _request(
    session: ClientConnection,
    message_types: tuple[int, int],
    payload: dict[str, Any],
    deadline: float,
    on_event: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    request_type, response_type = message_types
    message_id = uuid4().hex
    session.send(json.dumps({
        "clientMsgId": message_id,
        "payloadType": request_type,
        "payload": payload,
    }))
    while (remaining := deadline - time.monotonic()) > 0:
        message = _receive(session, remaining)
        if message.get("payloadType") == response_type and message.get("clientMsgId") == message_id:
            result = message.get("payload", {})
            if isinstance(result, dict):
                return result
            raise DemoConnectionError("INVALID_PROVIDER_RESPONSE")
        if on_event is not None:
            on_event(message)
    raise DemoConnectionError("PROVIDER_TIMEOUT")


def _receive(session: ClientConnection, timeout: float) -> dict[str, Any]:
    try:
        message = json.loads(session.recv(timeout=timeout))
    except TimeoutError:
        raise DemoConnectionError("PROVIDER_TIMEOUT") from None
    except (ValueError, TypeError, OSError, WebSocketException):
        raise DemoConnectionError("INVALID_OR_UNAVAILABLE_PROVIDER_RESPONSE") from None
    if not isinstance(message, dict):
        raise DemoConnectionError("INVALID_PROVIDER_RESPONSE")
    if message.get("payloadType") in ERROR_RESPONSES:
        raise DemoConnectionError("PROVIDER_REJECTED_REQUEST")
    return message


def demo_credentials() -> tuple[str, str, str, str]:
    login = os.getenv("ATLAS_CTRADER_DEMO_LOGIN", "").strip()
    client_id = os.getenv("ATLAS_CTRADER_CLIENT_ID", "").strip()
    client_secret = os.getenv("ATLAS_CTRADER_CLIENT_SECRET", "").strip()
    token = os.getenv("ATLAS_CTRADER_ACCESS_TOKEN", "").strip()
    if not (client_id and client_secret and token and login.isascii() and login.isdecimal()):
        raise DemoConnectionError("DEMO_LOGIN_AND_VIEW_ONLY_CREDENTIALS_REQUIRED")
    return client_id, client_secret, token, login


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


@contextmanager
def authenticated_demo(client_id: str, client_secret: str, token: str, login: str) -> Iterator[tuple[ClientConnection, int]]:
    with connect(DEMO_ENDPOINT, open_timeout=4, close_timeout=1, max_size=2**22) as session:
        deadline = time.monotonic() + 8
        _request(session, APPLICATION_AUTH, {"clientId": client_id, "clientSecret": client_secret}, deadline)
        accounts = _request(session, ACCOUNTS_BY_ACCESS_TOKEN, {"accessToken": token}, deadline)
        account_id = _account_id(accounts, login)
        account_request = {"ctidTraderAccountId": account_id}
        authorized = _request(session, ACCOUNT_AUTH, {**account_request, "accessToken": token}, deadline)
        if str(authorized.get("ctidTraderAccountId")) != str(account_id):
            raise DemoConnectionError("ACCOUNT_ID_MISMATCH")
        yield session, account_id


def _account_snapshot(client_id: str, client_secret: str, token: str, login: str) -> dict[str, Any]:
    with authenticated_demo(client_id, client_secret, token, login) as (session, account_id):
        deadline = time.monotonic() + 8
        account_request = {"ctidTraderAccountId": account_id}
        trader_result = _request(session, TRADER, account_request, deadline)
        trader = trader_result.get("trader")
        if (str(trader_result.get("ctidTraderAccountId")) != str(account_id)
                or not isinstance(trader, dict)
                or str(trader.get("ctidTraderAccountId")) != str(account_id)):
            raise DemoConnectionError("ACCOUNT_ID_MISMATCH")
        assets = _request(session, ASSET_LIST, account_request, deadline)
        if str(assets.get("ctidTraderAccountId")) != str(account_id):
            raise DemoConnectionError("ACCOUNT_ID_MISMATCH")

    deposit_asset = trader.get("depositAssetId")
    currency = next((
        asset.get("name") for asset in assets.get("asset", [])
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
    if not isinstance(broker, str) or "fxpro" not in broker.casefold():
        raise DemoConnectionError("FXPRO_CTRADER_BROKER_REQUIRED")
    return {
        "status": "CONNECTED",
        "environment": "DEMO",
        "access": "VIEW_ONLY",
        "login_masked": f"***{login[-4:]}",
        "broker": broker[:100] if isinstance(broker, str) else None,
        "balance": balance,
        "currency": currency[:16] if currency else None,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


def read_demo_account() -> dict[str, Any]:
    if not ctrader_selected():
        return {"status": "INACTIVE"}
    try:
        credentials = demo_credentials()
    except DemoConnectionError as exc:
        return {"status": "NOT_CONFIGURED", "reason": str(exc)}
    try:
        return _account_snapshot(*credentials)
    except DemoConnectionError as exc:
        return {"status": "UNAVAILABLE", "reason": str(exc)}
    except (OSError, ValueError, TypeError, WebSocketException):
        return {"status": "UNAVAILABLE", "reason": "PROVIDER_CONNECTION_FAILED"}
