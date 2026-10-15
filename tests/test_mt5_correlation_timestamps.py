"""Synthetic timestamp fixtures; these are not observed broker market data."""
import math
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.monitor import atlas_mt5
from app.risk.correlation import measure_correlations


NOW = datetime(2026, 10, 15, 12, 2, tzinfo=timezone.utc)
BAR_MS = 300_000
CURRENT_OPEN = int(NOW.timestamp() * 1000) // BAR_MS * BAR_MS


def histories(offset_seconds=0, stale_seconds=0):
    return {
        symbol: [
            {
                "open_time": CURRENT_OPEN - (199 - i) * BAR_MS
                + (offset_seconds - stale_seconds) * 1000,
                "close": math.exp(.001 * i + .01 * math.sin(i + phase)),
            }
            for i in range(200)
        ]
        for symbol, phase in [("EURUSD", 0), ("GBPUSD", .3)]
    }


def monitor_fixture(monkeypatch, tmp_path, *, offset=10800, broker_offset=None):
    monkeypatch.setenv("ATLAS_LIVE_TRADING", "false")
    monkeypatch.setenv("ATLAS_MT5_QUOTE_TIME_OFFSET_SECONDS", str(offset))
    monkeypatch.setenv("ATLAS_MT5_MAX_QUOTE_AGE_SECONDS", "30")
    monkeypatch.setenv("ATLAS_MAX_ABS_CORRELATION", ".8")
    monkeypatch.setenv("ATLAS_DEMO_LEDGER", str(tmp_path / "ledger.json"))
    monkeypatch.setenv("ATLAS_SIGNAL_JOURNAL", str(tmp_path / "signals.jsonl"))
    monkeypatch.setenv("ATLAS_COUNCIL_PROFILE", str(tmp_path / "profile.json"))
    monkeypatch.setattr(atlas_mt5, "mt5", SimpleNamespace(TIMEFRAME_M5=5))

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW

    monkeypatch.setattr(atlas_mt5, "datetime", Clock)
    monitor = atlas_mt5.AtlasMT5Monitor(symbols=["EURUSD"])
    data_offset = offset if broker_offset is None else broker_offset
    data = histories(data_offset)
    ticks = {symbol: {"time_msc": int((NOW.timestamp() + data_offset) * 1000)}
             for symbol in data}
    monkeypatch.setattr(monitor.broker, "candles", lambda symbol, *args: data[symbol])
    monkeypatch.setattr(monitor.broker, "quote", lambda symbol: ticks[symbol])
    return monitor, data, ticks


def context(monitor):
    return monitor._correlation_context(symbol="EURUSD", open_symbols=["GBPUSD"],
                                        snapshot_id="test", timestamp=NOW.isoformat())


@pytest.mark.parametrize("offset", [10800, -10800, 0])
def test_correlation_uses_all_completed_utc_bars_without_mutating_broker_data(monkeypatch, tmp_path, offset):
    monitor, data, _ = monitor_fixture(monkeypatch, tmp_path, offset=offset)
    original = deepcopy(data)
    result = context(monitor)
    assert result is not None
    assert result["sample_count"] == 198
    assert result["last_bar_closed_at"] == "2026-10-15T12:00:00+00:00"
    assert result["timestamp_offset_seconds"] == offset
    assert data == original


def test_wrong_broker_offset_cannot_select_old_bars_as_current(monkeypatch, tmp_path):
    monitor, _, _ = monitor_fixture(monkeypatch, tmp_path, offset=0, broker_offset=10800)
    assert context(monitor) is None


@pytest.mark.parametrize("bad_tick", [{}, {"time_msc": 0}, {"time_msc": "invalid"}])
def test_every_symbol_requires_a_trustworthy_quote(monkeypatch, tmp_path, bad_tick):
    monitor, _, ticks = monitor_fixture(monkeypatch, tmp_path)
    ticks["GBPUSD"] = bad_tick
    assert context(monitor) is None


def test_stale_peer_quote_invalidates_correlation(monkeypatch, tmp_path):
    monitor, _, ticks = monitor_fixture(monkeypatch, tmp_path)
    ticks["GBPUSD"]["time_msc"] -= 120_000
    assert context(monitor) is None


def test_stale_candles_are_rejected_after_normalization_even_with_fresh_ticks(monkeypatch, tmp_path):
    monitor, data, _ = monitor_fixture(monkeypatch, tmp_path)
    data.update(histories(offset_seconds=10800, stale_seconds=10800))
    assert context(monitor) is None


def test_correlation_rejects_future_bar_opens_instead_of_trimming_shifted_history():
    with pytest.raises(ValueError, match="future"):
        measure_correlations("EURUSD", ["GBPUSD"], histories(offset_seconds=10800),
                             limit=.8, snapshot_id="test", as_of=NOW.isoformat())


def test_current_incomplete_bar_is_excluded():
    result = measure_correlations("EURUSD", ["GBPUSD"], histories(),
                                  limit=.8, snapshot_id="test", as_of=NOW.isoformat())
    assert result["sample_count"] == 198
    assert result["last_bar_closed_at"] == "2026-10-15T12:00:00+00:00"
