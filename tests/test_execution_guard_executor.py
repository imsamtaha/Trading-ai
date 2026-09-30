from app.execution_guard.models import ExecutionRequest


class MT5:
    def __init__(self):
        self.orders = []

    def place_manual_order(self, user_id, order):
        self.orders.append((user_id, order))
        return {"status": "FILLED", "ticket": 42}


def test_demo_executor_is_the_only_component_that_calls_broker():
    from app.execution_guard.executor import DemoExecutor

    mt5 = MT5()
    executor = DemoExecutor(mt5)
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
