import json
from datetime import datetime, timezone

import pytest
from app.monitor.atlas_mt5 import AtlasMT5Monitor


def monitor_with_loss(tmp_path, monkeypatch, limit, loss):
    monkeypatch.setenv("ATLAS_LIVE_TRADING", "false")
    monkeypatch.setenv("ATLAS_DEMO_ACCOUNT_EQUITY", "10000")
    monkeypatch.setenv("ATLAS_COUNCIL_TRAINING_ENABLED", "false")
    monkeypatch.setenv("ATLAS_SHADOW_TRAINING_ENABLED", "false")
    monkeypatch.setenv("ATLAS_CATEGORY_POSITION_LIMIT", "0")
    monkeypatch.setenv("ATLAS_MT5_QUOTE_TIME_OFFSET_SECONDS", "0")
    if limit is None:
        monkeypatch.delenv("ATLAS_DEMO_MAX_DAILY_LOSS_PERCENT", raising=False)
    else:
        monkeypatch.setenv("ATLAS_DEMO_MAX_DAILY_LOSS_PERCENT", limit)
    for key, filename in (
        ("ATLAS_DEMO_LEDGER", "ledger.json"),
        ("ATLAS_SIGNAL_JOURNAL", "signals.jsonl"),
        ("ATLAS_COUNCIL_TRAINING_JOURNAL", "council.jsonl"),
        ("ATLAS_COUNCIL_PROFILE", "profile.json"),
    ):
        monkeypatch.setenv(key, str(tmp_path / filename))
    now = datetime.now(timezone.utc)
    (tmp_path / "ledger.json").write_text(json.dumps({
        "open_positions": [],
        "closed_trades": [{"symbol": "GBPUSD", "closed_at": now.isoformat(),
                          "risk_normalized_pnl": -loss}],
    }))
    monitor = AtlasMT5Monitor(symbols=["EURUSD"])
    monkeypatch.setattr(monitor.broker, "quote", lambda symbol: {
        "bid": 1.1000, "ask": 1.1002, "time_msc": int(now.timestamp() * 1000),
    })
    return monitor


@pytest.mark.parametrize("limit,loss,expected", [
    ("7", 305.15, "PAPER_TRADE_OPENED"),
    ("7", 699.99, "PAPER_TRADE_OPENED"),
    ("7", 700.00, "NO_TRADE"),
    ("7", 701.00, "NO_TRADE"),
    (None, 305.15, "NO_TRADE"),
])
def test_monitor_enforces_configured_daily_loss(tmp_path, monkeypatch, limit, loss, expected):
    monitor = monitor_with_loss(tmp_path, monkeypatch, limit, loss)
    candidate = {
        "direction": "LONG", "entry": 1.1002, "stop_loss": 1.0992,
        "take_profit": 1.1022, "strategy": "CONTINUATION_5M",
        "confidence": 85, "metadata": {"risk": {"risk_percent": 0.5}},
    }
    event = monitor._open_paper_trade(
        timestamp=datetime.now(timezone.utc).isoformat(), symbol="EURUSD",
        candidate=candidate, decision={"decision": "BUY"},
    )
    assert event["status"] == expected
    if expected == "NO_TRADE":
        assert "Daily loss limit reached" in event["reason"]
        assert event["risk"]["max_daily_loss_percent"] == float(limit or "3")
        assert len(monitor.ledger.open_positions()) == 0
    else:
        assert len(monitor.ledger.open_positions()) == 1
    assert monitor.execution.policy.enabled is False


@pytest.mark.parametrize("limit", ["0", "-1", "101", "nan", "inf", "invalid"])
def test_invalid_paper_daily_loss_limit_fails_closed(tmp_path, monkeypatch, limit):
    with pytest.raises(ValueError):
        monitor_with_loss(tmp_path, monkeypatch, limit, 0)
