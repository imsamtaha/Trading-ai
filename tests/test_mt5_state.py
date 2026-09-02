from types import SimpleNamespace

from app.execution.mt5 import MT5ExecutionError
from app.execution.mt5_state import MT5CockpitAdapter


class FakeConfig:
    dry_run = True


class FakeBroker:
    def __init__(self):
        self.config = FakeConfig()
        self.connected = False

    def connect(self):
        self.connected = True
        return {
            "login": 592031391,
            "server": "FxPro-MT5 Demo",
            "balance": 10000.0,
            "equity": 10025.0,
            "currency": "USD",
            "trade_allowed": False,
            "live_trading_enabled": False,
        }

    def ensure_connected(self):
        self.connected = True

    def symbol_info(self, symbol):
        if symbol != "EURUSD":
            raise MT5ExecutionError("not found")
        return SimpleNamespace()

    def quote(self, symbol):
        return {"symbol": symbol, "bid": 1.1, "ask": 1.1002, "last": 1.1001}

    def positions(self):
        return [
            {
                "ticket": 42,
                "symbol": "EURUSD",
                "direction": "LONG",
                "volume": 0.1,
                "price_open": 1.099,
                "sl": 1.09,
                "tp": 1.11,
                "profit": 25.0,
                "magic": 260830,
            }
        ]

    def disconnect(self):
        self.connected = False


def test_mt5_snapshot_normalizes_demo_account_and_positions():
    adapter = MT5CockpitAdapter(FakeBroker())
    state = adapter.snapshot(("EURUSD", "XAUUSD"))

    assert state["account"]["id"] == 592031391
    assert state["account"]["balance"] == 10000.0
    assert state["equity"]["equity"] == 10025.0
    assert state["equity"]["open_positions"] == 1
    assert state["equity"]["unrealized_pnl"] == 25.0
    assert state["prices"]["EURUSD"] == 1.1001
    assert state["resolved_symbols"]["EURUSD"] == "EURUSD"
    assert "XAUUSD" in state["symbol_errors"]
    assert state["broker"]["environment"] == "demo"
    assert state["broker"]["live_trading_enabled"] is False
