from tests.test_auto_execution import PortfolioBroker, validated_candidate, decision
from app.execution.auto import AutoExecutionCoordinator, AutoExecutionConfig


def test_fresh_portfolio_position_blocks_duplicate_symbol():
    broker = PortfolioBroker()
    snapshot = broker.risk_snapshot
    broker.risk_snapshot = lambda: {**snapshot(), "positions": [{"symbol": "EURUSD"}]}
    broker.volume_for_risk = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Sizing must not run"))
    result = AutoExecutionCoordinator(broker=broker, config=AutoExecutionConfig(enabled=True)).execute_candidate(
        symbol="EURUSD", candidate=validated_candidate(), decision=decision(),
        account={"login": 123, "server": "Test", "trade_mode": 0})
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "POSITION_ALREADY_OPEN"
    assert broker.orders == []
