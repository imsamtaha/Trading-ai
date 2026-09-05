from app.dashboard.market_briefing import MarketBriefingService


class FakeResponse:
    def __init__(self, payload=None, content=b""):
        self.payload = payload
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def get(self, url, **kwargs):
        if "quote" in url:
            return FakeResponse(
                {
                    "quoteResponse": {
                        "result": [
                            {
                                "symbol": "^GSPC",
                                "regularMarketPrice": 5100.25,
                                "regularMarketChange": 25.5,
                                "regularMarketChangePercent": 0.5,
                                "marketState": "REGULAR",
                            }
                        ]
                    }
                }
            )
        return FakeResponse(
            content=b"<rss><channel><item><title>Market headline</title><link>https://example.com/story</link><pubDate>Today</pubDate></item></channel></rss>"
        )


def test_briefing_keeps_market_context_separate_from_execution():
    data = MarketBriefingService(session=FakeSession()).briefing()

    assert data["status"] == "ONLINE"
    assert data["market_board"][1]["label"] == "S&P 500"
    assert data["market_board"][1]["price"] == 5100.25
    assert data["headlines"][0]["title"] == "Market headline"
    assert "never used by the execution gate" in data["disclaimer"]
