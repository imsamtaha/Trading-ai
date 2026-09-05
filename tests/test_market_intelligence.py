import json

from app.dashboard.market_intelligence import MarketIntelligenceFeed


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def test_market_feed_returns_provider_quotes_and_news():
    responses = iter([
        {"c": 512.2, "d": 2.1, "dp": 0.41, "t": 1_700_000_000},
        {"c": 438.5, "d": -1.3, "dp": -0.3, "t": 1_700_000_000},
        {"c": 391.2, "d": 0.5, "dp": 0.13, "t": 1_700_000_000},
        {"c": 210.4, "d": 1.1, "dp": 0.53, "t": 1_700_000_000},
        [{"headline": "Markets update", "source": "ATLAS Test", "url": "https://example.com", "datetime": 1_700_000_000}],
    ])

    feed = MarketIntelligenceFeed(
        api_key="test",
        http_get=lambda *_args, **_kwargs: FakeResponse(next(responses)),
        cache_seconds=30,
        now=lambda: 1_700_000_010,
    )

    state = feed.snapshot()

    assert state["status"] == "LIVE"
    assert len(state["markets"]) == 4
    assert state["markets"][0]["symbol"] == "SPY"
    assert state["news"][0]["headline"] == "Markets update"
    assert state["delayed"] is True


def test_market_feed_is_safe_when_not_configured():
    state = MarketIntelligenceFeed(api_key="").snapshot()

    assert state["status"] == "NOT_CONFIGURED"
    assert state["markets"] == []
    assert state["news"] == []
