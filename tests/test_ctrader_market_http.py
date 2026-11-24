import json

import pytest
from fastapi import HTTPException

from scripts import serve_ctrader_market as bridge


def test_market_bridge_filters_credentials_routes_and_response_fields(monkeypatch):
    monkeypatch.setenv("ATLAS_CTRADER_MARKET_TOKEN", "test-bridge-token")
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
    assert [(route.path, route.methods) for route in bridge.app.routes] == [("/api/ctrader/market-data", {"GET"})]
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
