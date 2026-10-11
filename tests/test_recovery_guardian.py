from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
import pytest

from app.intelligence.recovery_guardian import RecoveryGuardian
from app.monitor.atlas_mt5 import AtlasMT5Monitor

NOW = datetime(2026, 10, 11, 3, tzinfo=timezone.utc)

def outcome(index, result=-1.0, **patch):
    return {
        "id": f"paper-{index}", "symbol": "EURUSD", "strategy": "CONTINUATION_5M",
        "status": "CLOSED", "r_multiple": result,
        "closed_at": (NOW - timedelta(hours=12 * (index + 1))).isoformat(),
        "training_context": {"trade_intent": {
            "execution_environment": "PAPER", "broker_execution_allowed": False}},
        **patch,
    }

def candidate():
    return {"direction": "LONG", "entry": 100.0, "stop_loss": 99.0,
            "take_profit": 102.0, "strategy": "CONTINUATION_5M", "confidence": 85.0,
            "qualified": True, "regime": "BULL_TREND",
            "metadata": {"risk": {"risk_percent": 0.5}}}

def assess(agent, **patch):
    args = dict(symbol="EURUSD", candidate=candidate(),
                quote={"bid": 100.0, "ask": 100.1}, risk={"approved": True})
    args.update(patch)
    return agent.assess(**args)

def test_recovery_never_overrides_senior_risk():
    agent = RecoveryGuardian()
    agent.fit([], as_of=NOW)
    assert assess(agent, risk={"approved": False})["allowed"] is False
    assert assess(agent, risk={"approved": "true"})["allowed"] is False

def test_wide_spread_veto_and_safe_unknown_pair_collection():
    agent = RecoveryGuardian()
    agent.fit([], as_of=NOW)
    assert assess(agent, quote={"bid": 100, "ask": 100.5})["reason_codes"] == ["SPREAD_TOO_WIDE"]
    safe = assess(agent)
    assert safe["allowed"] is True
    assert safe["reason_codes"] == ["COLLECT_FORWARD_EVIDENCE"]
    assert safe["broker_execution_allowed"] is False

def test_negative_pair_quarantine_requires_samples_and_days():
    agent = RecoveryGuardian()
    agent.fit([outcome(i) for i in range(10)], as_of=NOW)
    assert assess(agent)["reason_codes"] == ["NEGATIVE_PAPER_EXPECTANCY"]
    report = agent.report(daily_loss_percent=7.17, daily_limit_percent=7, as_of=NOW)
    assert report["state"] == "SESSION_HALTED"
    assert report["closed_examples"] == 10
    assert len(report["quarantined_pairs"]) == 1
    agent.fit([outcome(i, closed_at=(NOW-timedelta(minutes=i+1)).isoformat()) for i in range(10)], as_of=NOW)
    assert assess(agent)["allowed"] is True
    agent.fit([outcome(i) for i in range(9)], as_of=NOW)
    assert assess(agent)["allowed"] is True

def test_recent_window_and_future_outcomes_do_not_leak():
    agent = RecoveryGuardian()
    rows = [outcome(i, 1.0 if i < 20 else -50.0) for i in range(40)]
    agent.fit(rows + [outcome(99, -1000, closed_at=(NOW+timedelta(seconds=1)).isoformat())], as_of=NOW)
    assert assess(agent)["allowed"] is True
    assert agent.closed_examples == 40
    assert agent.excluded_future == 1

@pytest.mark.parametrize("quote", [
    {"bid": 101, "ask": 100}, {"bid": float("nan"), "ask": 100},
    {"bid": 100, "ask": float("inf")}, {"bid": 0, "ask": 0},
])
def test_invalid_quotes_fail_closed(quote):
    agent = RecoveryGuardian()
    agent.fit([], as_of=NOW)
    assert assess(agent, quote=quote)["allowed"] is False

def test_invalid_paper_provenance_fails_closed_and_duplicates_not_inflated():
    agent = RecoveryGuardian()
    row = outcome(0)
    agent.fit([row, row], as_of=NOW)
    assert agent.closed_examples == 1
    assert agent.duplicates_ignored == 1
    agent.fit([outcome(0, training_context={"trade_intent":{
        "execution_environment":"LIVE", "broker_execution_allowed":True}})], as_of=NOW)
    assert assess(agent)["reason_codes"] == ["INVALID_PAPER_EVIDENCE"]

def test_monitor_uses_recovery_veto_without_broker_orders(tmp_path, monkeypatch):
    monkeypatch.setenv("ATLAS_LIVE_TRADING", "false")
    monkeypatch.setenv("ATLAS_AUTO_DISCOVER_SYMBOLS", "false")
    monkeypatch.setenv("ATLAS_RECOVERY_AGENT_ENABLED", "true")
    monkeypatch.setenv("ATLAS_RECOVERY_REPORT", str(tmp_path/"recovery.json"))
    monkeypatch.setenv("ATLAS_COUNCIL_TRAINING_ENABLED", "true")
    monkeypatch.setenv("ATLAS_DEMO_LEDGER", str(tmp_path/"ledger.json"))
    monkeypatch.setenv("ATLAS_COUNCIL_PROFILE", str(tmp_path/"profile.json"))
    monkeypatch.setenv("ATLAS_SIGNAL_JOURNAL", str(tmp_path/"signals.jsonl"))
    monitor = AtlasMT5Monitor(symbols=["EURUSD"])
    monitor.broker = Mock()
    tick = int(datetime.now(timezone.utc).timestamp()*1000)
    monitor.broker.quote.return_value = {"bid":100,"ask":100.5,"time_msc":tick}
    event = monitor._open_paper_trade(timestamp=datetime.now(timezone.utc).isoformat(),
        symbol="EURUSD",candidate=candidate(),decision={"decision":"BUY","confidence":82,"score":88,"risk_level":"LOW"})
    assert event["status"] == "NO_TRADE"
    assert event["recovery_guardian"]["reason_codes"] == ["SPREAD_TOO_WIDE"]
    assert monitor.ledger.open_positions() == []
    monitor.broker.order_send.assert_not_called()

def test_council_recovery_veto_is_authoritative_and_not_directional_training(tmp_path):
    from app.intelligence.council_adapters import build_paper_council, record_settled_paper_outcome
    from app.intelligence.council_training import CouncilTrainingJournal
    agent = RecoveryGuardian()
    agent.fit([], as_of=NOW)
    verdict = assess(agent, quote={"bid":100, "ask":100.5})
    package = build_paper_council(symbol="EURUSD", snapshot_id="snap",
        signal={"direction":"LONG","confidence":90}, risk={"approved":True},
        data_quality=1.0, recovery=verdict)
    assert package["trade_intent"]["decision"] == "HOLD"
    assert "RECOVERY_GUARDIAN_VETO" in package["trade_intent"]["reason_codes"]
    record = record_settled_paper_outcome(council=package["council"],
        trade_intent=package["trade_intent"], realized_direction="BUY",
        journal=CouncilTrainingJournal(tmp_path/"journal.jsonl"))
    assert all(item["agent"] != "recovery_guardian" for item in record["opinions"])
