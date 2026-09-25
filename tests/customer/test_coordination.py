from datetime import datetime, timezone

from app.customer.agents.capital_guardian import evaluate_capital
from app.customer.agents.confidence import calibrate_confidence
from app.customer.agents.coordinator import coordinate
from app.customer.contracts import (
    AgentStatus,
    AgentVerdict,
    CustomerContext,
    Decision,
    Mode,
    Signal,
)
from app.customer.realtime.snapshot import build_snapshot


def _snapshot(account=None, news=None):
    now = datetime.now(timezone.utc)
    return build_snapshot(
        context=CustomerContext("c1", "a1", Mode.LIVE_DEMO),
        symbol="EURUSD",
        timeframe="5m",
        market={"bid": 1.1, "ask": 1.1002, "timestamp": now.isoformat(), "trend": "bullish"},
        account=account or {"equity": 10000, "balance": 10000, "drawdown_pct": 1.0, "open_risk_pct": 1.0},
        system={"connector_ok": True},
        now=now,
        news=news,
        sentiment={"bias": "bullish"},
    )


def _v(snap, agent, signal, confidence=0.8, *, status=AgentStatus.OK, fresh=True, blockers=(), evidence=None):
    return AgentVerdict(
        agent=agent,
        timestamp=datetime.now(timezone.utc),
        snapshot_id=snap.snapshot_id,
        status=status,
        signal=signal,
        confidence=confidence,
        evidence=tuple(evidence or (f"{agent}:factor",)),
        blockers=tuple(blockers),
        data_quality={"fresh": fresh, "score": 1.0 if fresh else 0.0},
        latency_ms=1.0,
    )


def test_unavailable_or_stale_votes_do_not_win_by_simple_majority():
    snap = _snapshot()
    verdicts = [
        _v(snap, "a", Signal.LONG, status=AgentStatus.UNAVAILABLE, fresh=False),
        _v(snap, "b", Signal.LONG, status=AgentStatus.DEGRADED, fresh=False, blockers=("stale",)),
        _v(snap, "technical", Signal.SHORT, confidence=0.8),
    ]
    decision = coordinate(snap, verdicts)
    assert decision.decision is Decision.SELL


def test_high_impact_news_conflict_forces_wait():
    snap = _snapshot(news={"impact": "high", "bias": "bearish"})
    verdicts = [
        _v(snap, "technical", Signal.LONG, 0.9),
        _v(snap, "regime", Signal.LONG, 0.8),
        _v(snap, "news", Signal.SHORT, 0.9, evidence=("impact:high", "bias:bearish")),
    ]
    decision = coordinate(snap, verdicts)
    assert decision.decision is Decision.WAIT
    assert decision.blockers


def test_confidence_requires_independent_fresh_factors_and_penalizes_concentration():
    snap = _snapshot()
    one_source = [_v(snap, "technical", Signal.LONG, 0.95, evidence=("same",))]
    multi = [
        _v(snap, "technical", Signal.LONG, 0.9, evidence=("trend",)),
        _v(snap, "regime", Signal.LONG, 0.85, evidence=("regime",)),
        _v(snap, "sentiment", Signal.LONG, 0.8, evidence=("crowd",)),
    ]
    assert calibrate_confidence(one_source, Signal.LONG) < 0.85
    assert calibrate_confidence(multi, Signal.LONG) > calibrate_confidence(one_source, Signal.LONG)


def test_capital_guardian_vetoes_independently_of_consensus():
    snap = _snapshot(account={"equity": 9000, "balance": 10000, "drawdown_pct": 10.0, "open_risk_pct": 1.0})
    capital = evaluate_capital(snap, requested_risk_pct=1.0)
    assert capital.approved is False
    assert capital.blockers
