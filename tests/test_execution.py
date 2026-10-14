from app.execution.atlas import AtlasExecutionService, ExecutionPolicy
from app.intelligence.specialists import RiskExecutive
from app.risk.manager import calculate_risk


def approved_decision(action="BUY", risk_level="LOW", confidence=90):
    direction = "LONG" if action == "BUY" else "SHORT"
    stop, target = (98, 104) if action == "BUY" else (102, 96)
    risk = calculate_risk(direction, 100, stop, target)
    return {"decision": action, "confidence": confidence, "risk_level": risk_level,
            "symbol": "EURUSD", "snapshot_id": "s", "specialist_schema_version": 1,
            "risk_executive": RiskExecutive().assess(risk, symbol="EURUSD", snapshot_id="s")}


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
        approved_decision("SELL", confidence=72)
    )
    assert approved is True
    assert reason == "APPROVED"


def test_execution_gate_rejects_high_risk():
    service = AtlasExecutionService(
        broker=FakeBroker(),
        policy=ExecutionPolicy(enabled=True, max_risk_level="MEDIUM"),
    )
    approved, reason = service.gate(
        approved_decision(risk_level="HIGH")
    )
    assert approved is False
    assert reason == "RISK_LEVEL_BLOCKED"
