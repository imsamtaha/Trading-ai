from datetime import datetime, timedelta, timezone

from app.customer.agents.financial_monitor import FinancialMonitor
from app.customer.agents.news import NewsAgent
from app.customer.agents.regime import RegimeAgent
from app.customer.agents.sentiment import SentimentAgent
from app.customer.agents.system_watchdog import SystemWatchdog
from app.customer.agents.technical import TechnicalAgent
from app.customer.contracts import AgentStatus, CustomerContext, Mode
from app.customer.realtime.snapshot import build_snapshot


def _snapshot(*, stale=False, news=None, sentiment=None, connector_ok=True):
    now = datetime.now(timezone.utc)
    market_time = now - timedelta(minutes=5) if stale else now
    return build_snapshot(
        context=CustomerContext("c1", "a1", Mode.LIVE_DEMO),
        symbol="EURUSD",
        timeframe="5m",
        market={
            "bid": 1.1000,
            "ask": 1.1002,
            "timestamp": market_time.isoformat(),
            "trend": "bullish",
            "momentum": "positive",
            "volatility": 0.4,
        },
        account={"equity": 10000.0, "balance": 10000.0, "drawdown_pct": 1.0},
        system={"connector_ok": connector_ok, "latency_ms": 20},
        now=now,
        news=news,
        sentiment=sentiment,
    )


def test_all_specialists_emit_shared_verdict_contract():
    snap = _snapshot(news={"impact": "low", "bias": "neutral"}, sentiment={"bias": "bullish", "score": 0.4})
    agents = [TechnicalAgent(), NewsAgent(), SentimentAgent(), RegimeAgent(), FinancialMonitor(), SystemWatchdog()]
    for agent in agents:
        verdict = agent.evaluate(snap)
        assert verdict.agent
        assert verdict.snapshot_id == snap.snapshot_id
        assert verdict.timestamp.tzinfo is not None
        assert 0.0 <= verdict.confidence <= 1.0
        assert isinstance(verdict.evidence, tuple)
        assert isinstance(verdict.blockers, tuple)
        assert "fresh" in verdict.data_quality
        assert verdict.latency_ms >= 0


def test_missing_external_context_degrades_without_fabrication():
    snap = _snapshot(news=None, sentiment=None)
    assert NewsAgent().evaluate(snap).status is AgentStatus.UNAVAILABLE
    assert SentimentAgent().evaluate(snap).status is AgentStatus.UNAVAILABLE


def test_stale_or_broken_system_state_is_blocking():
    stale = _snapshot(stale=True, news={}, sentiment={})
    technical = TechnicalAgent().evaluate(stale)
    watchdog = SystemWatchdog().evaluate(stale)
    assert technical.status is AgentStatus.DEGRADED
    assert technical.blockers
    assert watchdog.status is AgentStatus.DEGRADED
    broken = _snapshot(news={}, sentiment={}, connector_ok=False)
    broken_watchdog = SystemWatchdog().evaluate(broken)
    assert broken_watchdog.status is AgentStatus.DEGRADED
    assert "connector" in " ".join(broken_watchdog.blockers).lower()
