from datetime import datetime, timezone

from app.customer.contracts import CustomerContext, Decision, DecisionCandidate, Mode
from app.customer.realtime.snapshot import build_snapshot
from app.customer.validation.calibration import CalibrationBook
from app.customer.validation.health import AgentHealthTracker, scenario_flags
from app.customer.validation.replay import replay_snapshots
from app.customer.validation.shadow import run_shadow


def _snapshot(**market_overrides):
    now = datetime.now(timezone.utc)
    market = {"bid": 1.1, "ask": 1.1002, "timestamp": now.isoformat(), "spread_points": 2, "volatility": 0.4}
    market.update(market_overrides)
    return build_snapshot(
        context=CustomerContext("c1", "a1", Mode.LIVE_DEMO),
        symbol="EURUSD",
        timeframe="5m",
        market=market,
        account={"equity": 10000, "balance": 10000},
        system={"connector_ok": True},
        now=now,
        news={"impact": "low"},
        sentiment={"bias": "neutral"},
    )


def _evaluator(snapshot):
    return DecisionCandidate(snapshot.snapshot_id, snapshot.customer_id, snapshot.account_id, snapshot.mode, Decision.WAIT, 0.5)


def test_replay_is_deterministic_for_same_snapshots_and_evaluator():
    snapshots = [_snapshot(), _snapshot()]
    first = replay_snapshots(snapshots, _evaluator)
    second = replay_snapshots(snapshots, _evaluator)
    assert first == second


def test_shadow_records_decision_without_execution():
    result = run_shadow(_snapshot(), _evaluator)
    assert result["executed"] is False
    assert result["decision"] == "WAIT"


def test_calibration_buckets_persist(tmp_path):
    path = tmp_path / "calibration.json"
    book = CalibrationBook(path)
    book.record(0.82, success=True)
    book.record(0.87, success=False)
    reloaded = CalibrationBook(path)
    metrics = reloaded.metrics()
    assert metrics["80-89"]["count"] == 2
    assert metrics["80-89"]["success_rate"] == 0.5


def test_agent_health_degrades_from_stale_error_and_latency_and_persists(tmp_path):
    path = tmp_path / "health.json"
    health = AgentHealthTracker(path)
    healthy = health.update("technical", stale=False, error=False, latency_ms=20)
    degraded = health.update("technical", stale=True, error=True, latency_ms=3000)
    assert degraded < healthy
    assert AgentHealthTracker(path).score("technical") == degraded


def test_scenario_flags_cover_abnormal_market_and_system_cases():
    snap = _snapshot(spread_points=80, volatility=2.0, gap_pct=1.5)
    flags = scenario_flags(snap, mt5_connected=False, duplicate_signal=True, conflicting_agents=True, rapid_drawdown_pct=4.0, high_impact_news=True)
    assert {"spread_spike", "volatility_spike", "gap", "mt5_disconnect", "duplicate_signal", "conflicting_agents", "rapid_drawdown", "high_impact_news"}.issubset(flags)
