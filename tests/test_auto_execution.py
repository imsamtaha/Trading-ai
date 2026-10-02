import time
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

    def risk_snapshot(self):
        return {"equity": 10000.0, "daily_realized_pnl": 0.0, "open_risk_percent": 0.0,
                "positions": self._positions, "timestamp": time.time()}

    def quote(self, symbol):
        return {"bid": 1.1000, "ask": 1.1002, "point": 0.00001, "time": int(time.time())}

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

    def market_order(self, symbol, direction, volume, stop_loss, take_profit, comment="ATLAS", **bounds):
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
        "qualified": True,
        "created_at": time.time(),
        "metadata": {"risk": {"approved": True, "risk_percent": 0.25}},
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



import time
import pytest


class PortfolioBroker(FakeBroker):
    def __init__(self, *, daily_pnl=0.0, open_risk=0.0, snapshot_error=False, quote_entry=1.1002):
        super().__init__()
        self.daily_pnl = daily_pnl
        self.open_risk = open_risk
        self.snapshot_error = snapshot_error
        self.quote_entry = quote_entry

    def risk_snapshot(self):
        from app.execution.mt5 import MT5ExecutionError
        if self.snapshot_error:
            raise MT5ExecutionError("History unavailable")
        return {"equity": 10000.0, "daily_realized_pnl": self.daily_pnl,
                "open_risk_percent": self.open_risk, "positions": [], "timestamp": time.time()}

    def quote(self, symbol):
        return {"bid": self.quote_entry - 0.0002, "ask": self.quote_entry,
                "point": 0.00001, "time": int(time.time()), "time_msc": int(time.time() * 1000)}


def validated_candidate(risk_percent=0.25):
    return {**candidate(), "qualified": True, "created_at": time.time(),
            "metadata": {"risk": {"approved": True, "risk_percent": risk_percent}}}


@pytest.mark.parametrize("broker", [PortfolioBroker(daily_pnl=-300), PortfolioBroker(open_risk=2.9),
                                    PortfolioBroker(snapshot_error=True)])
def test_auto_execution_blocks_portfolio_limits_and_unknown_history(broker):
    coordinator = AutoExecutionCoordinator(broker=broker, config=AutoExecutionConfig(enabled=True))
    result = coordinator.execute_candidate(symbol="EURUSD", candidate=validated_candidate(),
                                           decision=decision(), account={"equity": 10000})
    assert result["status"] == "BLOCKED"
    assert broker.orders == []


def test_auto_execution_preserves_strategy_risk_budget():
    broker = PortfolioBroker()
    c = validated_candidate(0.25)
    c.update(stop_loss=1.08, take_profit=1.14)
    result = AutoExecutionCoordinator(broker=broker, config=AutoExecutionConfig(enabled=True)).execute_candidate(
        symbol="EURUSD", candidate=c, decision=decision(), account={"equity": 10000})
    assert result["status"] == "FILLED"
    assert result["risk"]["risk_percent"] == 0.25
    assert result["risk"]["actual_risk_amount"] <= 25.0


@pytest.mark.parametrize("change", [{"entry": 1.05}, {"created_at": time.time() - 600},
                                    {"metadata": {}}, {"qualified": False}, {"entry": float("nan")}])
def test_auto_execution_rejects_invalid_or_stale_candidates(change):
    broker = PortfolioBroker()
    c = {**validated_candidate(), **change}
    result = AutoExecutionCoordinator(broker=broker, config=AutoExecutionConfig(enabled=True)).execute_candidate(
        symbol="EURUSD", candidate=c, decision=decision(), account={"equity": 10000})
    assert result["status"] == "BLOCKED"
    assert broker.orders == []


def test_auto_execution_blocks_excessive_entry_drift():
    broker = PortfolioBroker(quote_entry=1.15)
    result = AutoExecutionCoordinator(broker=broker, config=AutoExecutionConfig(enabled=True)).execute_candidate(
        symbol="EURUSD", candidate=validated_candidate(), decision=decision(), account={"equity": 10000})
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "ENTRY_DRIFT"
    assert broker.orders == []
