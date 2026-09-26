from app.execution.atlas import AtlasExecutionService, ExecutionPolicy
from app.execution.mt5 import MT5Config, REAL_MONEY_ACK


class FakeBroker:
    config = type("Config", (), {"dry_run": True})()

    def market_order(self, **kwargs):
        return {"status": "DRY_RUN", **kwargs}


def test_execution_disabled_by_default():
    service = AtlasExecutionService(
        broker=FakeBroker(),
        policy=ExecutionPolicy(enabled=False),
    )
    result = service.execute(
        symbol="EURUSD",
        decision={"decision": "BUY", "confidence": 90, "risk_level": "LOW"},
        volume=0.01,
        stop_loss=1.0,
        take_profit=2.0,
    )
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "LIVE_EXECUTION_DISABLED"


def test_execution_gate_accepts_low_risk_high_confidence():
    service = AtlasExecutionService(
        broker=FakeBroker(),
        policy=ExecutionPolicy(enabled=True, min_confidence=55, max_risk_level="MEDIUM"),
    )
    approved, reason = service.gate(
        {"decision": "SELL", "confidence": 72, "risk_level": "LOW"}
    )
    assert approved is True
    assert reason == "APPROVED"


def test_execution_gate_rejects_high_risk():
    service = AtlasExecutionService(
        broker=FakeBroker(),
        policy=ExecutionPolicy(enabled=True, max_risk_level="MEDIUM"),
    )
    approved, reason = service.gate(
        {"decision": "BUY", "confidence": 90, "risk_level": "HIGH"}
    )
    assert approved is False
    assert reason == "RISK_LEVEL_BLOCKED"


def test_real_money_execution_requires_live_flag_and_ack(monkeypatch):
    monkeypatch.setenv("ATLAS_LIVE_TRADING", "true")
    monkeypatch.setenv("ATLAS_REAL_MONEY_EXECUTION", "true")
    monkeypatch.setenv("ATLAS_REAL_MONEY_ACK", REAL_MONEY_ACK)

    config = MT5Config.from_env()

    assert config.dry_run is False
    assert config.real_money_execution is True
    assert config.real_money_ack == REAL_MONEY_ACK


def test_real_money_execution_is_off_by_default(monkeypatch):
    monkeypatch.delenv("ATLAS_LIVE_TRADING", raising=False)
    monkeypatch.delenv("ATLAS_REAL_MONEY_EXECUTION", raising=False)
    monkeypatch.delenv("ATLAS_REAL_MONEY_ACK", raising=False)

    config = MT5Config.from_env()

    assert config.dry_run is True
    assert config.real_money_execution is False
    assert config.real_money_ack == ""
