import json
from datetime import datetime, timedelta, timezone

import pytest

from app.intelligence.council_adapters import build_paper_council
from app.intelligence.paper_memory import SettledPaperSetup
from app.monitor.atlas_mt5 import AtlasMT5Monitor
from app.paper_trading.mt5_ledger import PaperLedgerError


def _monitor(tmp_path, monkeypatch):
    monkeypatch.setenv("ATLAS_LIVE_TRADING", "false")
    monkeypatch.setenv("ATLAS_AUTO_DISCOVER_SYMBOLS", "false")
    monkeypatch.setenv("ATLAS_COUNCIL_TRAINING_ENABLED", "true")
    monkeypatch.setenv("ATLAS_DEMO_LEDGER", str(tmp_path / "ledger.json"))
    monkeypatch.setenv("ATLAS_SIGNAL_JOURNAL", str(tmp_path / "signals.jsonl"))
    monkeypatch.setenv(
        "ATLAS_COUNCIL_TRAINING_JOURNAL", str(tmp_path / "training.jsonl")
    )
    monkeypatch.setenv("ATLAS_COUNCIL_PROFILE", str(tmp_path / "profile.json"))
    monkeypatch.setenv("ATLAS_COUNCIL_MINIMUM_SAMPLES", "5")
    return AtlasMT5Monitor(symbols=["EURUSD"])


def _candidate():
    return {
        "direction": "LONG",
        "entry": 1.1000,
        "stop_loss": 1.0990,
        "take_profit": 1.1020,
        "strategy": "CONTINUATION_5M",
        "confidence": 85.0,
        "qualified": True,
        "regime": "BULL_TREND",
        "metadata": {"risk": {"risk_percent": 0.5}},
    }


def _decision():
    return {
        "decision": "BUY",
        "score": 88.0,
        "confidence": 82.0,
        "risk_level": "LOW",
        "conflict_score": 0.0,
        "event_risk_score": 0.0,
        "volatility_score": 0.0,
    }


def _fresh_quote(*, bid=1.1000, ask=1.1001):
    now_msc = int(datetime.now(timezone.utc).timestamp() * 1000)
    return {
        "bid": bid,
        "ask": ask,
        "time": now_msc // 1000,
        "time_msc": now_msc,
    }


def test_council_context_is_persisted_with_open_paper_trade(tmp_path, monkeypatch):
    monitor = _monitor(tmp_path, monkeypatch)
    monkeypatch.setattr(monitor.broker, "quote", lambda symbol: _fresh_quote())

    event = monitor._open_paper_trade(
        timestamp=datetime.now(timezone.utc).isoformat(),
        symbol="EURUSD",
        candidate=_candidate(),
        decision=_decision(),
    )

    assert event["status"] == "PAPER_TRADE_OPENED"
    assert event["trade_intent"]["decision"] == "BUY"
    assert event["trade_intent"]["execution_environment"] == "PAPER"
    assert event["trade_intent"]["broker_execution_allowed"] is False

    saved = monitor.ledger.open_positions()[0]
    context = saved["training_context"]
    assert context["trade_intent"]["decision"] == "BUY"
    assert context["trade_intent"]["broker_execution_allowed"] is False
    assert context["council"]["senior_risk_management"]["assessment"] == "RISK_ACCEPTABLE"


def test_winning_paper_close_records_training_and_refreshes_profile(tmp_path, monkeypatch):
    monitor = _monitor(tmp_path, monkeypatch)
    monkeypatch.setattr(monitor.broker, "quote", lambda symbol: _fresh_quote())

    opened = monitor._open_paper_trade(
        timestamp=datetime.now(timezone.utc).isoformat(),
        symbol="EURUSD",
        candidate=_candidate(),
        decision=_decision(),
    )
    assert opened["status"] == "PAPER_TRADE_OPENED"

    target = float(opened["trade"]["take_profit"])
    monkeypatch.setattr(
        monitor.broker,
        "quote",
        lambda symbol: _fresh_quote(bid=target + 0.0001, ask=target + 0.0002),
    )

    events = monitor._close_due_positions(datetime.now(timezone.utc).isoformat())

    assert len(events) == 1
    assert events[0]["status"] == "PAPER_TRADE_CLOSED"
    assert events[0]["training"]["realized_direction"] == "BUY"
    assert events[0]["training"]["total_examples"] == 1

    examples = monitor.council_training_journal.load()
    assert len(examples) == 1
    assert examples[0].realized_direction == "BUY"

    profile = monitor._load_council_profile()
    assert profile["total_examples"] == 1
    assert profile["agents"]["technical"]["weight"] == 1.0
    assert profile["agents"]["technical"]["locked_baseline"] is True


def test_losing_long_paper_close_trains_opposite_realized_direction(tmp_path, monkeypatch):
    monitor = _monitor(tmp_path, monkeypatch)
    monkeypatch.setattr(monitor.broker, "quote", lambda symbol: _fresh_quote())

    opened = monitor._open_paper_trade(
        timestamp=datetime.now(timezone.utc).isoformat(),
        symbol="EURUSD",
        candidate=_candidate(),
        decision=_decision(),
    )
    assert opened["status"] == "PAPER_TRADE_OPENED"

    stop = float(opened["trade"]["stop_loss"])
    monkeypatch.setattr(
        monitor.broker,
        "quote",
        lambda symbol: _fresh_quote(bid=stop - 0.0001, ask=stop),
    )

    events = monitor._close_due_positions(datetime.now(timezone.utc).isoformat())

    assert events[0]["training"]["realized_direction"] == "SELL"
    examples = monitor.council_training_journal.load()
    assert len(examples) == 1
    assert examples[0].realized_direction == "SELL"


@pytest.mark.parametrize("quote_override, reason", [
    ({"time_msc": 1}, "stale"),
    ({"time_msc": "invalid"}, "invalid"),
    ({"bid": float("inf"), "ask": float("inf")}, "Invalid quote"),
])
def test_unusable_quote_cannot_close_or_train_paper_trade(tmp_path, monkeypatch, quote_override, reason):
    monitor = _monitor(tmp_path, monkeypatch)
    monkeypatch.setattr(monitor.broker, "quote", lambda symbol: _fresh_quote())
    timestamp = datetime.now(timezone.utc).isoformat()
    opened = monitor._open_paper_trade(
        timestamp=timestamp, symbol="EURUSD", candidate=_candidate(), decision=_decision(),
    )
    assert opened["status"] == "PAPER_TRADE_OPENED"
    target = float(opened["trade"]["take_profit"])
    bad_quote = {**_fresh_quote(bid=target, ask=target + 0.0001), **quote_override}
    monkeypatch.setattr(monitor.broker, "quote", lambda symbol: bad_quote)

    events = monitor._close_due_positions(timestamp)

    assert len(events) == 1
    assert events[0]["status"] == "MT5_ERROR"
    assert reason in events[0]["reason"]
    assert len(monitor.ledger.open_positions()) == 1
    assert monitor.council_training_journal.load() == []


def test_training_disabled_preserves_legacy_paper_path(tmp_path, monkeypatch):
    monkeypatch.setenv("ATLAS_LIVE_TRADING", "false")
    monkeypatch.setenv("ATLAS_AUTO_DISCOVER_SYMBOLS", "false")
    monkeypatch.setenv("ATLAS_COUNCIL_TRAINING_ENABLED", "false")
    monkeypatch.setenv("ATLAS_DEMO_LEDGER", str(tmp_path / "ledger.json"))
    monkeypatch.setenv("ATLAS_SIGNAL_JOURNAL", str(tmp_path / "signals.jsonl"))
    monitor = AtlasMT5Monitor(symbols=["EURUSD"])
    monkeypatch.setattr(monitor.broker, "quote", lambda symbol: _fresh_quote())

    event = monitor._open_paper_trade(
        timestamp=datetime.now(timezone.utc).isoformat(),
        symbol="EURUSD",
        candidate=_candidate(),
        decision=_decision(),
    )

    assert event["status"] == "PAPER_TRADE_OPENED"
    assert event["trade"]["training_context"] is None
    assert event["council"] is None
    assert event["trade_intent"] is None


def _archived_trades(*, weak_holdout=False):
    now = datetime.now(timezone.utc)
    rows = []
    for index in range(24):
        opened = now - timedelta(days=30 - index)
        outcome = -1.0 if index % 4 == 0 or (weak_holdout and index >= 16) else 1.5
        context = build_paper_council(
            symbol="EURUSD", snapshot_id=f"archive-{index}",
            signal={"direction": "LONG", "confidence": 80.0},
            risk={"approved": True}, data_quality=1.0,
        )
        rows.append({
            "status": "CLOSED", "id": f"paper-{index}", "symbol": "EURUSD",
            "strategy": "CONTINUATION_5M", "timeframe": "5m", "direction": "LONG",
            "opened_at": opened.isoformat(),
            "closed_at": (opened + timedelta(hours=1)).isoformat(),
            "r_multiple": outcome, "training_context": context,
        })
    return rows


@pytest.mark.parametrize(("weak_holdout", "applied"), [(False, True), (True, False)])
def test_archived_paper_memory_only_increases_size_after_positive_holdout(
    tmp_path, monkeypatch, weak_holdout, applied
):
    source = tmp_path / "archive.json"
    trades = _archived_trades(weak_holdout=weak_holdout)
    invalid = {**trades[0], "execution_environment": "LIVE"}
    legacy = {**trades[0], "training_context": None}
    source.write_text(json.dumps({"closed_trades": [*trades, trades[0], invalid, legacy]}))
    monkeypatch.setenv("ATLAS_COUNCIL_HISTORY_LEDGER", str(source))
    first = _monitor(tmp_path, monkeypatch)
    assert first.ledger.closed_trades() == []
    first.council_training_journal.append(SettledPaperSetup.from_trade(trades[0]).example)

    # Reload from the persisted ledger archive and journal together.
    monitor = _monitor(tmp_path, monkeypatch)
    assert monitor.council_profile["total_examples"] == 24
    assert monitor.ledger.closed_trades() == []
    monkeypatch.setattr(monitor.broker, "quote", lambda _: _fresh_quote(bid=100.0, ask=100.01))
    candidate = {**_candidate(), "entry": 100, "stop_loss": 97, "take_profit": 106}

    event = monitor._open_paper_trade(
        timestamp=datetime.now(timezone.utc).isoformat(),
        symbol="EURUSD", candidate=candidate, decision=_decision(),
    )

    assert event["status"] == "PAPER_TRADE_OPENED"
    assert event["trade_intent"]["broker_execution_allowed"] is False
    trade = event["trade"]
    evidence = trade["training_context"].get("paper_sizing_experiment")
    assert trade["risk_percent"] == (0.55 if applied else 0.5)
    assert bool(evidence) is applied
    if applied:
        assert trade["position_size"] == pytest.approx(55 / 3)
        assert evidence["holdout_samples"] == 8


def test_position_limit_is_checked_under_ledger_lock(tmp_path, monkeypatch):
    monitor = _monitor(tmp_path, monkeypatch)
    monitor.ledger.open_trade(
        symbol="XAUUSD", direction="LONG", entry=100, stop_loss=98, take_profit=104,
        position_size=125, risk={"risk_percent": 2.5, "actual_risk_amount": 250},
        strategy="test", confidence=85, timeframe="5m", decision={},
    )

    with pytest.raises(PaperLedgerError, match="Aggregate open-risk"):
        monitor.ledger.open_trade(
            symbol="EURUSD", direction="LONG", entry=100, stop_loss=98, take_profit=104,
            position_size=27.5, risk={"risk_percent": 0.55, "actual_risk_amount": 55},
            strategy="test", confidence=85, timeframe="5m", decision={}, account_balance=10000,
        )

    assert len(monitor.ledger.open_positions()) == 1
