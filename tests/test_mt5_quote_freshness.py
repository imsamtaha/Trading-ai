from datetime import datetime, timezone

from app.monitor.atlas_mt5 import AtlasMT5Monitor


def make_monitor(monkeypatch):
    monkeypatch.setenv("ATLAS_LIVE_TRADING", "false")
    monkeypatch.setenv("ATLAS_MT5_MAX_QUOTE_AGE_SECONDS", "30")
    return AtlasMT5Monitor(symbols=["EURUSD"])


def test_fresh_mt5_quote_is_accepted(monkeypatch):
    monitor = make_monitor(monkeypatch)
    now_msc = int(datetime.now(timezone.utc).timestamp() * 1000)

    valid, reason = monitor._validate_quote_freshness({
        "time": now_msc // 1000,
        "time_msc": now_msc,
    })

    assert valid is True
    assert reason == ""


def test_stale_mt5_quote_is_rejected(monkeypatch):
    monitor = make_monitor(monkeypatch)
    stale_msc = int((datetime.now(timezone.utc).timestamp() - 120) * 1000)

    valid, reason = monitor._validate_quote_freshness({
        "time": stale_msc // 1000,
        "time_msc": stale_msc,
    })

    assert valid is False
    assert "stale" in reason.lower()


def test_missing_mt5_quote_timestamp_is_rejected(monkeypatch):
    monitor = make_monitor(monkeypatch)

    valid, reason = monitor._validate_quote_freshness({
        "time": 0,
        "time_msc": 0,
    })

    assert valid is False
    assert "timestamp is missing" in reason.lower()
