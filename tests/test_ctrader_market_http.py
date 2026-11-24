import json

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.integrations import ctrader_bridge as bridge
from scripts.serve_ctrader_market import app


def test_market_bridge_filters_credentials_routes_and_response_fields(monkeypatch):
    monkeypatch.setenv("ATLAS_CTRADER_MARKET_TOKEN", "test-bridge-token")
    monkeypatch.setenv("ATLAS_BROKER_PROVIDER", "ctrader")
    calls = []

    class FakeProvider:
        def connect(self):
            calls.append("connect")

        def disconnect(self):
            calls.append("disconnect")

        def quote(self, symbol):
            assert symbol == "XAUUSD"
            return {"bid": 4100.0, "ask": 4100.4, "time_msc": 1795531240000, "account": "private"}

        def candles(self, symbol, timeframe, count):
            assert (symbol, timeframe, count) == ("XAUUSD", "1h", 120)
            return [{"open_time": 1795528800000, "open": 4100.0, "close": 4103.0,
                     "high": 4105.0, "low": 4099.0, "volume": 100}]

    monkeypatch.setattr(bridge, "CTraderMarketData", FakeProvider)
    monkeypatch.setattr(bridge, "_cache", {})
    with TestClient(app) as client:
        assert client.post("/api/ctrader/market-data").status_code == 405
        assert client.get("/api/ctrader/account").status_code == 404
    with pytest.raises(HTTPException) as missing:
        bridge.market_data("XAUUSD", 60, None)
    assert missing.value.status_code == 401
    auth = "Bearer test-bridge-token"
    with pytest.raises(HTTPException) as invalid:
        bridge.market_data("invalid", 60, auth)
    assert invalid.value.status_code == 400
    assert calls == []
    response = bridge.market_data("XAUUSD", 60, auth)
    assert response.status_code == 200
    data = json.loads(response.body)
    assert data["environment"] == "DEMO" and data["access"] == "VIEW_ONLY"
    assert data["quote"] == {"bid": 4100.0, "ask": 4100.4, "timeMsc": 1795531240000}
    assert data["candles"] == [{"time": 1795528800, "open": 4100.0, "close": 4103.0, "high": 4105.0, "low": 4099.0}]
    assert json.loads(bridge.market_data("XAUUSD", 60, auth).body) == data
    assert calls == ["connect", "disconnect"]


def test_missing_current_quote_preserves_closed_candles(monkeypatch):
    class NoSpot:
        def connect(self):
            pass

        def disconnect(self):
            pass

        def quote(self, symbol):
            raise bridge.DemoConnectionError("CURRENT_TWO_SIDED_QUOTE_UNAVAILABLE")

        def candles(self, symbol, timeframe, count):
            return [{"open_time": 1795528800000, "open": 4100.0, "close": 4103.0, "high": 4105.0, "low": 4099.0}]

    monkeypatch.setattr(bridge, "CTraderMarketData", NoSpot)
    result = bridge.market_snapshot("XAUUSD", 60)
    assert result["quote"] is None and result["quoteReason"] == "CURRENT_QUOTE_UNAVAILABLE"
    assert len(result["candles"]) == 1
    assert bridge.market_snapshot("XAUUSD", 10080)["candles"] == []


def test_tiger_shield_pauses_mt5_and_exposes_only_authenticated_market_bridge(monkeypatch):
    from app.main import app as dashboard_app

    monkeypatch.setenv("ATLAS_BROKER_PROVIDER", "ctrader")
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    monkeypatch.setenv("ATLAS_CTRADER_MARKET_TOKEN", "test-bridge-token")
    monkeypatch.setattr(bridge, "market_snapshot", lambda asset, interval: {
        "source": "ctrader-demo", "asset": asset, "interval": interval,
    })
    monkeypatch.setattr(bridge, "_cache", {})
    with TestClient(dashboard_app) as client:
        assert client.get("/health").json()["mt5_paused"] is True
        page = client.get("/traders", follow_redirects=True).text
        assert "cTrader demo workspace" in page
        assert '<script src="/ui/setups-panel.js">' not in page
        assert 'href="/connect/fxpro-mt5"' not in page
        for url in ("/connect/fxpro-mt5/", "/dashboard/active-setups", "/mt5/status"):
            response = client.get(url)
            assert response.status_code == 503
            assert response.json()["status"] == "PAUSED"
        assert client.post("/connect/fxpro-mt5/verify").status_code == 503
        assert client.post("/agent/paper/execute").status_code == 503
        endpoint = "/api/ctrader/market-data?asset=XAUUSD&interval=60"
        assert client.get(endpoint).status_code == 401
        response = client.get(endpoint, headers={"Authorization": "Bearer test-bridge-token"})
        assert response.status_code == 200 and response.json()["source"] == "ctrader-demo"
        assert client.post(endpoint).status_code == 403
