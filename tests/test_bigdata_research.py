"""Regression tests for the isolated Bigdata research adapter."""
from datetime import datetime, timezone, timedelta
import pytest

from app.intelligence.bigdata_research import normalize_research_record, normalize_research_batch


NOW = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)


def test_sourced_record_is_research_only():
    item = normalize_research_record(
        {"title": "Macro release", "url": "https://example.com/story",
         "timestamp": "2026-10-20T11:00:00Z", "asset": "XAUUSD"},
        now=NOW,
    )
    assert item["provider"] == "bigdata"
    assert item["signal_action"] == "HOLD"
    assert item["broker_execution_allowed"] is False
    assert item["paper_only"] is True
    assert item["stale"] is False


@pytest.mark.parametrize("record", [
    {}, {"title": "No source", "timestamp": "2026-10-20T11:00:00Z"},
    {"title": "Unsafe URL", "url": "http://example.com", "timestamp": "2026-10-20T11:00:00Z"},
    {"title": "Missing timezone", "url": "https://example.com", "timestamp": "2026-10-20T11:00:00"},
    {"title": "Future", "url": "https://example.com", "timestamp": "2026-10-21T11:00:00Z"},
])
def test_invalid_research_fails_closed(record):
    with pytest.raises(ValueError):
        normalize_research_record(record, now=NOW)


def test_stale_record_is_marked():
    item = normalize_research_record(
        {"title": "Old news", "url": "https://example.com", "timestamp": "2026-10-18T11:00:00Z"},
        now=NOW,
    )
    assert item["stale"] is True


def test_batch_rejects_invalid_input():
    with pytest.raises(ValueError):
        normalize_research_batch({})
