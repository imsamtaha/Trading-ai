from datetime import datetime, timezone

from app.dashboard.market_briefing import MarketBriefingService


class FakeResponse:
    def __init__(self, payload=None, content=b""):
        self.status_code = 200
        self.payload = payload
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def get(self, url, **kwargs):
        if "/v8/finance/chart/" in url:
            return FakeResponse(
                {
                    "chart": {
                        "result": [
                            {
                                "meta": {
                                    "regularMarketPrice": 5100.25,
                                    "chartPreviousClose": 5074.75,
                                    "regularMarketTime": datetime.now(timezone.utc).timestamp(),
                                },
                                "indicators": {"quote": [{"close": [5074.75, 5100.25]}]},
                            }
                        ],
                        "error": None,
                    }
                }
            )
        from email.utils import format_datetime
        link = 'https://www.bbc.com/arabic/articles/story' if 'bbci' in url else url.replace('/rss/press.html', '/press/story').replace('/feeds/press_monetary.xml', '/newsevents/story')
        return FakeResponse(content=f"<rss><channel><item><title>Market headline</title><link>{link}</link><pubDate>{format_datetime(datetime.now(timezone.utc))}</pubDate></item></channel></rss>".encode())


def test_briefing_keeps_market_context_separate_from_execution():
    data = MarketBriefingService(session=FakeSession()).briefing()

    assert data["status"] == "ONLINE"
    assert data["market_board"][1]["label"] == "S&P 500"
    assert data["market_board"][1]["price"] == 5100.25
    assert data["market_board"][1]["freshness"] == "FRESH"
    assert data["headlines"][0]["title"] == "Market headline"
    assert data["market_analysis"]["execution"] == "DISABLED"
    assert "never used by the execution gate" in data["disclaimer"]

