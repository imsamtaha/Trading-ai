from types import SimpleNamespace

import pytest

from app.customer.realtime.runtime import MT5DemoRuntime
from app.execution.mt5 import MT5ExecutionError


class FakeDemoBroker:
    def __init__(self, trade_mode=0):
        self.connected = False
        self.trade_mode = trade_mode
        self.orders = []
    def connect(self):
        self.connected = True
        return {"login": 123, "trade_mode": self.trade_mode, "trade_allowed": True, "equity": 10000.0, "balance": 10000.0}
    def quote(self, symbol):
        return {"symbol": symbol, "bid": 1.1000, "ask": 1.1002, "spread_points": 2.0, "time": 1760000000}
    def candles(self, symbol, timeframe, count):
        return [{"open_time": i, "open":1.0, "high":1.01, "low":0.99, "close":1.0, "volume":100, "close_time":i} for i in range(count)]
    def market_order(self, **kwargs):
        self.orders.append(kwargs)
        return {"status":"FILLED", "ticket":42, **kwargs}
    def disconnect(self):
        self.connected = False


def test_mt5_demo_runtime_uses_demo_broker_and_runs_customer_cycle(monkeypatch):
    fake_mt5 = SimpleNamespace(TIMEFRAME_M5=5, TIMEFRAME_M15=15, TIMEFRAME_M30=30, TIMEFRAME_H1=60, ACCOUNT_TRADE_MODE_DEMO=0)
    monkeypatch.setattr("app.customer.realtime.runtime.mt5", fake_mt5)
    monkeypatch.setattr("app.customer.realtime.runtime.analyze_candles", lambda candles: {
        "price":1.1002, "trend":"bullish", "momentum":"bullish",
        "indicators":{"atr_14":0.001},
    })
    broker = FakeDemoBroker(0)
    result = MT5DemoRuntime(lambda: broker).run(customer_id="c1", account_id="123", symbol="EURUSD", timeframe="5m", demo_volume=0.1, requested_risk_pct=1.0)
    assert result["mode"] == "LIVE_DEMO"
    assert result["status"] in {"EXECUTED", "BLOCKED"}
    assert result["trace_id"]
    assert broker.connected is False


def test_mt5_demo_runtime_rejects_real_account(monkeypatch):
    fake_mt5 = SimpleNamespace(TIMEFRAME_M5=5, TIMEFRAME_M15=15, TIMEFRAME_M30=30, TIMEFRAME_H1=60, ACCOUNT_TRADE_MODE_DEMO=0)
    monkeypatch.setattr("app.customer.realtime.runtime.mt5", fake_mt5)
    broker = FakeDemoBroker(2)
    with pytest.raises(MT5ExecutionError, match="demo account"):
        MT5DemoRuntime(lambda: broker).run(customer_id="c1", account_id="123", symbol="EURUSD", timeframe="5m", demo_volume=0.1, requested_risk_pct=1.0)
    assert broker.orders == []
    assert broker.connected is False
