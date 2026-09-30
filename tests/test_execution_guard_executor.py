from app.execution_guard.models import ExecutionRequest
from app.execution_guard.executor import DemoExecutor, DemoExecutionDisabled


class MT5:
    def __init__(self):
        self.orders = []

    def place_manual_order(self, user_id, order):
        self.orders.append((user_id, order))
        return {"status": "FILLED", "ticket": 42}


def test_demo_executor_is_the_only_component_that_calls_broker():
    mt5 = MT5()
    executor = DemoExecutor(mt5, execution_enabled=lambda: True)
    request = ExecutionRequest(
        request_id="decision-001",
        account_type="DEMO",
        symbol="EURUSD",
        direction="BUY",
        volume=0.01,
        stop_loss=1.09,
        take_profit=1.11,
    )

    result = executor.execute("alice", request)

    assert result["status"] == "FILLED"
    assert result["ticket"] == 42
    assert len(mt5.orders) == 1
    assert mt5.orders[0][0] == "alice"
    assert mt5.orders[0][1]["confirmed"] is True


def test_demo_executor_blocks_when_runtime_switch_is_off():
    mt5 = MT5()
    request = ExecutionRequest(
        request_id="decision-002", account_type="DEMO", symbol="XAUUSD",
        direction="BUY", volume=0.01, stop_loss=2290.0, take_profit=2310.0,
    )
    executor = DemoExecutor(mt5, execution_enabled=lambda: False)
    try:
        executor.execute("alice", request)
    except DemoExecutionDisabled:
        pass
    else:
        raise AssertionError("demo execution should be blocked when runtime switch is off")
    assert mt5.orders == []
