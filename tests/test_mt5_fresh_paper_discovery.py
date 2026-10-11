"""Paper monitor must scan only broker-full symbols with fresh MT5 ticks when enabled."""
from datetime import datetime, timezone
from unittest.mock import Mock

from app.monitor.atlas_mt5 import AtlasMT5Monitor


def _symbol(name, *, seconds_old=0, mode=4):
    broker_now = datetime.now(timezone.utc).timestamp() + 10800 - seconds_old
    return {
        "symbol": name,
        "bid": 1.1,
        "ask": 1.1001,
        "point": 0.0001,
        "visible": True,
        "tradeable": True,
        "trade_mode": mode,
        "time": int(broker_now),
        "time_msc": int(broker_now * 1000),
    }


def test_paper_scan_ignores_stale_and_close_only_quotes(monkeypatch, tmp_path):
    monkeypatch.setenv("ATLAS_LIVE_TRADING", "false")
    monkeypatch.setenv("ATLAS_DEMO_LEDGER", str(tmp_path / "ledger.json"))
    monkeypatch.setenv("ATLAS_MT5_QUOTE_TIME_OFFSET_SECONDS", "10800")
    monkeypatch.setenv("ATLAS_MONITOR_FRESH_QUOTES_ONLY", "true")
    monitor = AtlasMT5Monitor(top_n=12)
    monitor.broker.symbols = Mock(return_value=[
        _symbol("BTCUSDm"),
        _symbol("EURUSD.fx", seconds_old=300),
        _symbol("XAUUSDm", seconds_old=600),
        _symbol("WTI", mode=3),
    ])
    assert monitor.discover_symbols() == ["BTCUSDm"]


def test_paper_scan_auto_resumes_after_fresh_quotes(monkeypatch, tmp_path):
    monkeypatch.setenv("ATLAS_LIVE_TRADING", "false")
    monkeypatch.setenv("ATLAS_DEMO_LEDGER", str(tmp_path / "ledger.json"))
    monkeypatch.setenv("ATLAS_MT5_QUOTE_TIME_OFFSET_SECONDS", "10800")
    monkeypatch.setenv("ATLAS_MONITOR_FRESH_QUOTES_ONLY", "true")
    monitor = AtlasMT5Monitor(top_n=12)
    monitor.broker.symbols = Mock(return_value=[
        _symbol("BTCUSDm"), _symbol("EURUSD.fx", seconds_old=1000),
    ])
    assert monitor.discover_symbols() == ["BTCUSDm"]
    monitor.broker.symbols.return_value = [
        _symbol("BTCUSDm"), _symbol("EURUSD.fx"),
    ]
    assert set(monitor.discover_symbols()) == {"BTCUSDm", "EURUSD.fx"}
