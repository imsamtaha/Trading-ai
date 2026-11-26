import json

import pytest
from fastapi import HTTPException

from app.dashboard.api import atlas_dashboard_state
from app.dashboard.fxpro_onboarding import current_fxpro_demo_account
from app.execution.mt5 import MT5Broker, MT5ExecutionError
from app.integrations import ctrader_demo
from app.integrations.mt5_bridge import RemoteMT5BridgeError, fetch_remote_mt5_telemetry


class DemoSession:
    def __init__(self, scope="SCOPE_VIEW", live=False):
        self.sent = []
        self.responses = {
            2100: (2101, {}),
            2149: (2150, {
                "permissionScope": scope,
                "ctidTraderAccount": [
                    {"ctidTraderAccountId": 987654321, "traderLogin": 12345678, "isLive": live},
                    {"ctidTraderAccountId": 2222, "traderLogin": 11111111, "isLive": False},
                ],
            }),
            2102: (2103, {"ctidTraderAccountId": 987654321}),
            2121: (2122, {
                "ctidTraderAccountId": 987654321,
                "trader": {
                    "ctidTraderAccountId": 987654321, "brokerName": "FxPro Demo",
                    "balance": 178905, "moneyDigits": 2, "depositAssetId": 3,
                },
            }),
            2112: (2113, {"ctidTraderAccountId": 987654321, "asset": [{"assetId": 3, "name": "USD"}]}),
        }

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def send(self, message):
        self.sent.append(json.loads(message))

    def recv(self, timeout):
        sent = self.sent[-1]
        response_type, response = self.responses[sent["payloadType"]]
        return json.dumps({
            "clientMsgId": sent["clientMsgId"], "payloadType": response_type, "payload": response,
        })


@pytest.fixture
def demo_env(monkeypatch):
    for name, value in {
        "ATLAS_BROKER_PROVIDER": "ctrader",
        "ATLAS_CTRADER_DEMO_LOGIN": "12345678",
        "ATLAS_CTRADER_CLIENT_ID": "test-client",
        "ATLAS_CTRADER_CLIENT_SECRET": "test-secret",
        "ATLAS_CTRADER_ACCESS_TOKEN": "test-token",
    }.items():
        monkeypatch.setenv(name, value)


def test_demo_snapshot_uses_only_demo_view_requests(monkeypatch, demo_env):
    session = DemoSession()

    def open_demo(url, **kwargs):
        assert url == "wss://demo.ctraderapi.com:5036"
        return session

    monkeypatch.setattr(ctrader_demo, "connect", open_demo)
    account = ctrader_demo.read_demo_account()
    assert account["status"] == "CONNECTED"
    assert account["login_masked"] == "***5678"
    assert account["balance"] == "1789.05"
    assert account["currency"] == "USD"
    assert [request["payloadType"] for request in session.sent] == [2100, 2149, 2102, 2121, 2112]
    for request in session.sent[2:]:
        assert request["payload"]["ctidTraderAccountId"] == 987654321
    payload = json.dumps(account)
    assert "12345678" not in payload and "987654321" not in payload and "test-secret" not in payload


@pytest.mark.parametrize(("scope", "live", "reason"), [
    ("SCOPE_TRADE", False, "VIEW_ONLY_AUTHORIZATION_REQUIRED"),
    ("SCOPE_VIEW", True, "DEMO_LOGIN_NOT_UNIQUE_OR_NOT_AUTHORIZED"),
])
def test_demo_rejects_live_accounts_and_trading_scope(monkeypatch, demo_env, scope, live, reason):
    session = DemoSession(scope, live)
    monkeypatch.setattr(ctrader_demo, "connect", lambda *args, **kwargs: session)
    assert ctrader_demo.read_demo_account() == {"status": "UNAVAILABLE", "reason": reason}
    assert [request["payloadType"] for request in session.sent] == [2100, 2149]


def test_ctrader_rejects_non_fxpro_broker(monkeypatch, demo_env):
    session = DemoSession()
    session.responses[2121][1]["trader"]["brokerName"] = "Other Broker"
    monkeypatch.setattr(ctrader_demo, "connect", lambda *args, **kwargs: session)
    assert ctrader_demo.read_demo_account() == {
        "status": "UNAVAILABLE", "reason": "FXPRO_CTRADER_BROKER_REQUIRED"
    }


def test_ctrader_selection_pauses_mt5_before_connecting(demo_env, monkeypatch):
    monkeypatch.setenv("ATLAS_MT5_BRIDGE_URL", "https://example.invalid")
    with pytest.raises(MT5ExecutionError, match="paused"):
        MT5Broker().connect()
    with pytest.raises(RemoteMT5BridgeError, match="paused"):
        fetch_remote_mt5_telemetry()
    with pytest.raises(RuntimeError, match="paused"):
        current_fxpro_demo_account()
    with pytest.raises(HTTPException) as error:
        atlas_dashboard_state()
    assert error.value.status_code == 503
    assert "paused" in error.value.detail
