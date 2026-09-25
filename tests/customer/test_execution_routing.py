from dataclasses import replace
from datetime import datetime, timezone

import pytest

from app.customer.agents.trader import TraderAgent
from app.customer.contracts import CustomerContext, Decision, DecisionCandidate, Mode
from app.customer.execution.demo_adapter import DemoAdapter
from app.customer.execution.mode_router import ModeRouter
from app.customer.execution.production_adapter import ProductionAdapter
from app.customer.realtime.snapshot import build_snapshot


class FakeBroker:
    def __init__(self, connected=True):
        self.connected = connected
        self.calls = []

    def market_order(self, **kwargs):
        self.calls.append(kwargs)
        return {"status": "FILLED", "ticket": 123, **kwargs}


def _snapshot(mode=Mode.LIVE_DEMO):
    now = datetime.now(timezone.utc)
    return build_snapshot(
        context=CustomerContext("c1", "a1", mode),
        symbol="EURUSD",
        timeframe="5m",
        market={"bid": 1.1000, "ask": 1.1002, "timestamp": now.isoformat()},
        account={"equity": 10000, "balance": 10000},
        system={"connector_ok": True},
        now=now,
    )


def _decision(snap):
    return DecisionCandidate(snap.snapshot_id, snap.customer_id, snap.account_id, snap.mode, Decision.BUY, 0.82)


def test_trader_only_builds_structured_intent_and_has_no_broker_dependency():
    snap = _snapshot()
    trader = TraderAgent()
    intent = trader.build_intent(snap, _decision(snap), entry=1.1002, stop_loss=1.0980, take_profit=1.1046)
    assert intent.direction == "LONG"
    assert intent.customer_id == "c1"
    assert not hasattr(trader, "broker")


def test_trader_rejects_invalid_stop_target_geometry():
    snap = _snapshot()
    with pytest.raises(ValueError):
        TraderAgent().build_intent(snap, _decision(snap), entry=1.1, stop_loss=1.11, take_profit=1.12)


def test_router_rejects_risk_and_stale_connector_and_is_idempotent():
    snap = _snapshot()
    intent = TraderAgent().build_intent(snap, _decision(snap), entry=1.1002, stop_loss=1.0980, take_profit=1.1046)
    broker = FakeBroker()
    router = ModeRouter(DemoAdapter(broker))
    blocked = router.execute_demo(intent, {"approved": False, "reason": "risk", "volume": 0.1}, trace_id="t1")
    assert blocked.status == "BLOCKED"
    assert not broker.calls

    offline = FakeBroker(connected=False)
    offline_router = ModeRouter(DemoAdapter(offline))
    assert offline_router.execute_demo(intent, {"approved": True, "volume": 0.1}, trace_id="t2").status == "BLOCKED"

    first = router.execute_demo(intent, {"approved": True, "volume": 0.1}, trace_id="t3")
    second = router.execute_demo(intent, {"approved": True, "volume": 0.1}, trace_id="t3")
    assert first == second
    assert len(broker.calls) == 1


def test_client_payload_cannot_switch_demo_router_to_production():
    snap = _snapshot()
    intent = TraderAgent().build_intent(snap, _decision(snap), entry=1.1002, stop_loss=1.0980, take_profit=1.1046)
    broker = FakeBroker()
    router = ModeRouter(DemoAdapter(broker))
    result = router.execute_demo(intent, {"approved": True, "volume": 0.1, "mode": "LIVE_EXECUTION"}, trace_id="t4")
    assert result.mode is Mode.LIVE_DEMO
    with pytest.raises(RuntimeError):
        ProductionAdapter().execute(intent, {"approved": True}, trace_id="p1")
