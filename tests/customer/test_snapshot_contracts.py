from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from app.customer.contracts import (
    AgentStatus,
    CustomerContext,
    Decision,
    Mode,
    Signal,
)
from app.customer.realtime.snapshot import build_snapshot, snapshot_is_stale


def _now():
    return datetime.now(timezone.utc)


def test_customer_context_requires_customer_account_and_mode():
    ctx = CustomerContext(customer_id="c1", account_id="a1", mode=Mode.LIVE_DEMO)
    assert ctx.customer_id == "c1"
    assert ctx.account_id == "a1"
    assert ctx.mode is Mode.LIVE_DEMO
    with pytest.raises(ValueError):
        CustomerContext(customer_id="", account_id="a1", mode=Mode.LIVE_DEMO)


def test_snapshot_is_immutable_and_keeps_same_cycle_identity():
    now = _now()
    snap = build_snapshot(
        context=CustomerContext("c1", "a1", Mode.LIVE_DEMO),
        symbol="EURUSD",
        timeframe="5m",
        market={"bid": 1.1, "ask": 1.1002, "timestamp": now.isoformat()},
        account={"equity": 10000.0},
        system={"connector_ok": True},
        now=now,
    )
    assert snap.snapshot_id
    assert snap.customer_id == "c1"
    assert snap.account_id == "a1"
    assert snap.mode is Mode.LIVE_DEMO
    with pytest.raises(FrozenInstanceError):
        snap.symbol = "GBPUSD"


def test_stale_market_timestamp_is_detected():
    now = _now()
    stale = now - timedelta(minutes=3)
    snap = build_snapshot(
        context=CustomerContext("c1", "a1", Mode.LIVE_DEMO),
        symbol="EURUSD",
        timeframe="5m",
        market={"bid": 1.1, "ask": 1.1002, "timestamp": stale.isoformat()},
        account={"equity": 10000.0},
        system={"connector_ok": True},
        now=now,
    )
    assert snapshot_is_stale(snap, max_age_seconds=60) is True


def test_public_enums_are_explicit():
    assert AgentStatus.OK.value == "OK"
    assert Signal.LONG.value == "LONG"
    assert Decision.WAIT.value == "WAIT"
