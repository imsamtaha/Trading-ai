from datetime import datetime, timedelta, timezone

from app.customer.agents.rescue import RescueAction, RescueAgent
from app.customer.audit import AuditStore
from app.customer.contracts import CustomerContext, Mode
from app.customer.monitoring.notifications import build_notification
from app.customer.monitoring.position_monitor import PositionMonitor
from app.customer.realtime.snapshot import build_snapshot


def _snapshot(*, stale=False, connector_ok=True, volatility=0.4, spread_points=2, trend="bullish"):
    now = datetime.now(timezone.utc)
    market_time = now - timedelta(minutes=5) if stale else now
    return build_snapshot(
        context=CustomerContext("c1", "a1", Mode.LIVE_DEMO),
        symbol="EURUSD",
        timeframe="5m",
        market={
            "bid": 1.1,
            "ask": 1.1002,
            "timestamp": market_time.isoformat(),
            "volatility": volatility,
            "spread_points": spread_points,
            "trend": trend,
        },
        account={"equity": 10000, "balance": 10000},
        system={"connector_ok": connector_ok},
        now=now,
    )


def _position(**overrides):
    base = {"ticket": 7, "symbol": "EURUSD", "direction": "LONG", "entry": 1.1, "unrealized_loss_pct": 0.2}
    base.update(overrides)
    return base


def test_rescue_handles_market_and_system_deterioration():
    agent = RescueAgent()
    assert agent.evaluate(_position(), _snapshot(stale=True)).action is RescueAction.HALT
    assert agent.evaluate(_position(), _snapshot(connector_ok=False)).action is RescueAction.HALT
    assert agent.evaluate(_position(), _snapshot(volatility=2.0)).action is RescueAction.REDUCE
    assert agent.evaluate(_position(), _snapshot(spread_points=80)).action is RescueAction.PROTECT
    assert agent.evaluate(_position(), _snapshot(trend="bearish")).action is RescueAction.EXIT
    assert agent.evaluate(_position(unrealized_loss_pct=4.0), _snapshot()).action is RescueAction.EXIT


def test_rescue_is_independent_and_works_from_reloaded_position_dict():
    reloaded = dict(_position(direction="SHORT"))
    fresh_agent = RescueAgent()
    result = fresh_agent.evaluate(reloaded, _snapshot(trend="bullish"))
    assert result.action is RescueAction.EXIT
    assert not hasattr(fresh_agent, "trader")


def test_position_monitor_audit_and_notification_share_trace():
    store = AuditStore()
    monitor = PositionMonitor(RescueAgent(), audit_store=store)
    snap = _snapshot(volatility=2.0)
    decision = monitor.evaluate(_position(), snap, trace_id="trace-1")
    assert store.events[-1]["trace_id"] == "trace-1"
    assert store.events[-1]["customer_id"] == "c1"
    note = build_notification(snap, trace_id="trace-1", event="RESCUE", payload={"action": decision.action.value})
    assert note["trace_id"] == "trace-1"
    assert note["customer_id"] == "c1"
