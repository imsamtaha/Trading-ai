"""Linux-safe, fake-socket regression tests for FxPro LIVE view-only status."""
import json

from fastapi.testclient import TestClient
import pytest

from app.integrations import ctrader_demo
from scripts import atlas_provider_status as service


class LiveSession:
    def __init__(self, *, scope="SCOPE_VIEW", is_live=True, broker="FxPro International"):
        self.sent = []
        self.replies = {
            2100: (2101, {}),
            2149: (2150, {
                "permissionScope": scope,
                "ctidTraderAccount": [
                    {"ctidTraderAccountId": 345612, "traderLogin": 8675309, "isLive": is_live},
                ],
            }),
            2102: (2103, {"ctidTraderAccountId": 345612}),
            2121: (2122, {
                "ctidTraderAccountId": 345612,
                "trader": {
                    "ctidTraderAccountId": 345612, "brokerName": broker,
                    "balance": 125050, "moneyDigits": 2, "depositAssetId": 3,
                },
            }),
            2112: (2113, {
                "ctidTraderAccountId": 345612,
                "asset": [{"assetId": 3, "name": "USD"}],
            }),
        }

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def send(self, raw):
        self.sent.append(json.loads(raw))

    def recv(self, timeout):
        request = self.sent[-1]
        code, payload = self.replies[request["payloadType"]]
        return json.dumps({
            "clientMsgId": request["clientMsgId"],
            "payloadType": code,
            "payload": payload,
        })


@pytest.fixture
def live_env(monkeypatch):
    settings = {
        "ATLAS_BROKER_PROVIDER": "mt5",  # status never switches the selected provider
        "ATLAS_LIVE_TRADING": "false",
        "ATLAS_CTRADER_LIVE_LOGIN": "8675309",
        "ATLAS_CTRADER_LIVE_CLIENT_ID": "live-view-client",
        "ATLAS_CTRADER_LIVE_CLIENT_SECRET": "live-secret",
        "ATLAS_CTRADER_LIVE_ACCESS_TOKEN": "live-view-token",
    }
    for key, value in settings.items():
        monkeypatch.setenv(key, value)


def test_live_uses_live_endpoint_with_only_view_requests(live_env, monkeypatch):
    session = LiveSession()

    def open_live(url, **kwargs):
        assert url == "wss://live.ctraderapi.com:5036"
        return session

    monkeypatch.setattr(ctrader_demo, "connect", open_live)
    account = ctrader_demo.read_live_account()
    assert account["status"] == "CONNECTED"
    assert account["environment"] == "LIVE"
    assert account["access"] == "VIEW_ONLY"
    assert account["login_masked"] == "***5309"
    assert account["balance"] == "1250.50"
    assert [r["payloadType"] for r in session.sent] == [2100, 2149, 2102, 2121, 2112]
    text = json.dumps(account)
    for secret in ["8675309", "345612", "live-view-token", "live-secret"]:
        assert secret not in text


@pytest.mark.parametrize(("scope", "is_live", "broker", "reason"), [
    ("SCOPE_TRADE", True, "FxPro", "VIEW_ONLY_AUTHORIZATION_REQUIRED"),
    ("SCOPE_VIEW", False, "FxPro", "LIVE_LOGIN_NOT_UNIQUE_OR_NOT_AUTHORIZED"),
    ("SCOPE_VIEW", True, "Other Broker", "FXPRO_CTRADER_BROKER_REQUIRED"),
])
def test_live_fail_closed(live_env, monkeypatch, scope, is_live, broker, reason):
    session = LiveSession(scope=scope, is_live=is_live, broker=broker)
    monkeypatch.setattr(ctrader_demo, "connect", lambda *args, **kwargs: session)
    assert ctrader_demo.read_live_account() == {"status": "UNAVAILABLE", "reason": reason}
    if scope != "SCOPE_VIEW" or not is_live:
        assert [r["payloadType"] for r in session.sent] == [2100, 2149]


def test_live_not_configured_makes_no_external_call(monkeypatch):
    monkeypatch.delenv("ATLAS_CTRADER_LIVE_LOGIN", raising=False)
    monkeypatch.setenv("ATLAS_LIVE_TRADING", "false")
    monkeypatch.setattr(ctrader_demo, "connect", lambda *args, **kwargs: pytest.fail("Network call"))
    result = ctrader_demo.read_live_account()
    assert result["status"] == "NOT_CONFIGURED"


def test_live_refuses_execution_enabled_flag(live_env, monkeypatch):
    monkeypatch.setenv("ATLAS_LIVE_TRADING", "true")
    monkeypatch.setattr(ctrader_demo, "connect", lambda *args, **kwargs: pytest.fail("Network call"))
    assert ctrader_demo.read_live_account() == {
        "status": "UNAVAILABLE", "reason": "LIVE_TRADING_MUST_REMAIN_DISABLED",
    }


def test_live_status_has_distinct_auth_and_never_exposes_login(live_env, monkeypatch):
    monkeypatch.setenv("ATLAS_PROVIDER_STATUS_TOKEN", "demo-status-only")
    monkeypatch.setenv("ATLAS_PROVIDER_LIVE_STATUS_TOKEN", "live-status-only")
    monkeypatch.setattr(service, "read_live_account", lambda: {
        "status": "CONNECTED", "environment": "LIVE", "access": "VIEW_ONLY",
        "as_of": "2026-11-28T00:00:00Z", "balance": "1250.50",
        "currency": "USD", "broker": "FxPro", "login_masked": "***5309",
    })
    client = TestClient(service.app)
    uri = "/status/ctrader/live"
    assert client.get(uri).status_code == 401
    assert client.get(uri, headers={"Authorization": "Bearer demo-status-only"}).status_code == 401
    assert client.post(uri, headers={"Authorization": "Bearer live-status-only"}).status_code == 405
    response = client.get(uri, headers={"Authorization": "Bearer live-status-only"})
    assert response.status_code == 200
    assert response.json() == {
        "status": "CONNECTED", "environment": "LIVE", "access": "READ_ONLY",
        "brokerOrders": False, "asOf": "2026-11-28T00:00:00Z",
        "balance": 1250.5, "currency": "USD", "broker": "FxPro",
    }
    assert "5309" not in response.text
    assert response.headers["cache-control"] == "private, no-store"


def test_live_status_requires_configured_distinct_token(live_env, monkeypatch):
    monkeypatch.setenv("ATLAS_PROVIDER_STATUS_TOKEN", "demo-status-only")
    monkeypatch.delenv("ATLAS_PROVIDER_LIVE_STATUS_TOKEN", raising=False)
    monkeypatch.setattr(service, "read_live_account", lambda: pytest.fail("Provider call"))
    response = TestClient(service.app).get(
        "/status/ctrader/live", headers={"Authorization": "Bearer demo-status-only"}
    )
    assert response.status_code == 503


def test_live_status_rejects_mislabelled_demo_response(live_env, monkeypatch):
    monkeypatch.setenv("ATLAS_PROVIDER_LIVE_STATUS_TOKEN", "live-status-only")
    monkeypatch.setattr(service, "read_live_account", lambda: {
        "status": "CONNECTED", "environment": "DEMO", "access": "VIEW_ONLY",
    })
    response = TestClient(service.app).get(
        "/status/ctrader/live", headers={"Authorization": "Bearer live-status-only"}
    )
    assert response.status_code == 503
