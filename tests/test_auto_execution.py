from types import SimpleNamespace

from app.execution.auto import AutoExecutionConfig, AutoExecutionCoordinator
from app.execution.mt5 import MT5Config


class FakeBroker:
    def __init__(self, *, dry_run=False):
        self.config = MT5Config(dry_run=dry_run)
        self.orders = []
        self._positions = []

    def positions(self, symbol=None):
        return list(self._positions)

    def quote(self, symbol):
        return {"bid": 1.1000, "ask": 1.1002}

    def symbol_info(self, symbol):
        return SimpleNamespace(
            trade_tick_size=0.0001,
            trade_tick_value=10.0,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
        )

    def _normalized_volume(self, symbol, volume):
        return round(max(0.01, min(100.0, int(volume / 0.01) * 0.01)), 2)

    def volume_for_risk(self, symbol, entry, stop_loss, risk_amount):
        info = self.symbol_info(symbol)
        ticks = abs(entry - stop_loss) / info.trade_tick_size
        return self._normalized_volume(symbol, risk_amount / (ticks * info.trade_tick_value))

    def market_order(self, symbol, direction, volume, stop_loss, take_profit, comment="ATLAS"):
        order = {
            "status": "FILLED",
            "symbol": symbol,
            "side": direction,
            "volume": volume,
            "sl": stop_loss,
            "tp": take_profit,
        }
        self.orders.append(order)
        return order


def candidate():
    return {
        "direction": "LONG",
        "entry": 1.1000,
        "stop_loss": 1.0990,
        "take_profit": 1.1020,
        "confidence": 80.0,
    }


def decision():
    return {
        "decision": "BUY",
        "confidence": 80.0,
        "risk_level": "LOW",
    }


def test_auto_execution_blocked_when_switch_off():
    coordinator = AutoExecutionCoordinator(
        broker=FakeBroker(),
        config=AutoExecutionConfig(enabled=False),
    )
    result = coordinator.execute_candidate(
        symbol="EURUSD",
        candidate=candidate(),
        decision=decision(),
        account={"equity": 10000.0},
    )
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "AUTO_EXECUTION_DISABLED"


def test_auto_execution_requires_live_trading():
    coordinator = AutoExecutionCoordinator(
        broker=FakeBroker(dry_run=True),
        config=AutoExecutionConfig(enabled=True),
    )
    result = coordinator.execute_candidate(
        symbol="EURUSD",
        candidate=candidate(),
        decision=decision(),
        account={"equity": 10000.0},
    )
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "LIVE_TRADING_DISABLED"


def test_auto_execution_routes_through_risk_and_execution_gate():
    broker = FakeBroker()
    coordinator = AutoExecutionCoordinator(
        broker=broker,
        config=AutoExecutionConfig(enabled=True, risk_percent=1.0),
    )
    result = coordinator.execute_candidate(
        symbol="EURUSD",
        candidate=candidate(),
        decision=decision(),
        account={"equity": 10000.0},
    )
    assert result["status"] == "FILLED"
    assert result["risk"]["approved"] is True
    assert result["volume"] > 0
    assert len(broker.orders) == 1


def test_auto_execution_blocks_duplicate_symbol_position():
    broker = FakeBroker()
    broker._positions = [{"symbol": "EURUSD"}]
    coordinator = AutoExecutionCoordinator(
        broker=broker,
        config=AutoExecutionConfig(enabled=True),
    )
    result = coordinator.execute_candidate(
        symbol="EURUSD",
        candidate=candidate(),
        decision=decision(),
        account={"equity": 10000.0},
    )
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "POSITION_ALREADY_OPEN"
    assert broker.orders == []


def test_runtime_status_reports_execution_boundary(monkeypatch):
    monkeypatch.setenv("ATLAS_AUTO_EXECUTION_ENABLED", "false")
    monkeypatch.setenv("ATLAS_LIVE_TRADING", "false")
    from fastapi.testclient import TestClient
    from app.main import app

    body = TestClient(app).get("/runtime/status").json()
    assert body["auto_execution"]["effective_execution_enabled"] is False
    assert body["evolution"]["execution_access"] is False
    assert body["pipeline"][-1] == "mt5"
