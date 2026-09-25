from datetime import datetime, timedelta, timezone

from app.customer.audit import AuditStore
from app.customer.contracts import CustomerContext, Mode
from app.customer.execution.demo_adapter import DemoAdapter
from app.customer.realtime.cycle import CustomerRealtimeCycle
from app.customer.realtime.snapshot import build_snapshot


class FakeBroker:
    def __init__(self, connected=True):
        self.connected = connected
        self.calls = []

    def market_order(self, **kwargs):
        self.calls.append(kwargs)
        return {"status": "FILLED", "ticket": 9001, **kwargs}


def _snapshot(*, customer="c1", account="a1", stale=False, connector_ok=True):
    now = datetime.now(timezone.utc)
    market_time = now - timedelta(minutes=5) if stale else now
    return build_snapshot(
        context=CustomerContext(customer, account, Mode.LIVE_DEMO),
        symbol="EURUSD",
        timeframe="5m",
        market={
            "bid": 1.1000,
            "ask": 1.1002,
            "timestamp": market_time.isoformat(),
            "trend": "bullish",
            "momentum": "positive",
            "volatility": 0.4,
            "spread_points": 2,
        },
        account={"equity": 10000, "balance": 10000, "drawdown_pct": 0.5, "open_risk_pct": 0.5},
        system={"connector_ok": connector_ok, "latency_ms": 20},
        now=now,
        news={"impact": "low", "bias": "neutral"},
        sentiment={"bias": "bullish", "score": 0.5},
    )


def test_live_demo_cycle_is_auditable_end_to_end():
    broker = FakeBroker()
    store = AuditStore()
    cycle = CustomerRealtimeCycle(DemoAdapter(broker), audit_store=store)
    result = cycle.run(
        _snapshot(),
        stop_loss=1.0982,
        take_profit=1.1042,
        requested_risk_pct=1.0,
        demo_volume=0.1,
        trace_id="e2e-1",
    )
    assert result["status"] == "EXECUTED"
    assert result["decision"] == "BUY"
    assert result["rescue"] == "HOLD"
    assert result["notification"]["trace_id"] == "e2e-1"
    assert len(broker.calls) == 1
    events = store.by_trace("e2e-1", customer_id="c1")
    names = {e["event"] for e in events}
    assert {"SNAPSHOT", "AGENTS", "DECISION", "CAPITAL", "RISK", "EXECUTION", "RESCUE", "NOTIFICATION"}.issubset(names)


def test_stale_data_and_mt5_disconnect_block_new_demo_execution():
    broker = FakeBroker()
    cycle = CustomerRealtimeCycle(DemoAdapter(broker))
    stale = cycle.run(_snapshot(stale=True), stop_loss=1.0982, take_profit=1.1042, demo_volume=0.1, trace_id="stale")
    assert stale["status"] == "BLOCKED"
    assert broker.calls == []

    offline_broker = FakeBroker(connected=False)
    offline_cycle = CustomerRealtimeCycle(DemoAdapter(offline_broker))
    offline = offline_cycle.run(_snapshot(), stop_loss=1.0982, take_profit=1.1042, demo_volume=0.1, trace_id="offline")
    assert offline["status"] == "BLOCKED"
    assert offline_broker.calls == []


def test_duplicate_trace_is_idempotent_and_cross_customer_audit_is_not_visible():
    broker = FakeBroker()
    store = AuditStore()
    cycle = CustomerRealtimeCycle(DemoAdapter(broker), audit_store=store)
    snap = _snapshot()
    first = cycle.run(snap, stop_loss=1.0982, take_profit=1.1042, demo_volume=0.1, trace_id="same")
    second = cycle.run(snap, stop_loss=1.0982, take_profit=1.1042, demo_volume=0.1, trace_id="same")
    assert first["execution"] == second["execution"]
    assert len(broker.calls) == 1
    assert store.by_trace("same", customer_id="other") == []
