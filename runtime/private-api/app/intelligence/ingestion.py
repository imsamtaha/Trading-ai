from datetime import datetime, timezone

from app.intelligence.sources import (
    SourceReliability,
)


class EventIngestion:

    def __init__(self):

        self.source_engine = (
            SourceReliability()
        )

        self.events = []

    def ingest(
        self,
        title,
        source_id,
        category,
        published_at,
        affected_assets=None,
        raw_sentiment="NEUTRAL",
    ):

        source = self.source_engine.get(
            source_id
        )

        event = {
            "title": title,
            "source_id": source_id,
            "source": source.name,
            "source_reliability": (
                source.reliability
            ),
            "official": source.official,
            "category": category,
            "published_at": published_at,
            "ingested_at": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
            "affected_assets": (
                affected_assets or []
            ),
            "raw_sentiment": raw_sentiment,
        }

        self.events.append(event)

        return event

    def recent_events(self, limit=20):

        return self.events[-limit:]


if __name__ == "__main__":

    ingestion = EventIngestion()

    event = ingestion.ingest(
        title="Example FOMC event",
        source_id="federal_reserve",
        category="FED",
        published_at=(
            "2026-08-20T14:00:00+00:00"
        ),
        affected_assets=[
            "BTCUSDT",
            "XAUUSD",
            "USD",
        ],
        raw_sentiment="NEUTRAL",
    )

    print()
    print("EVENT INGESTION TEST")
    print("=" * 40)
    print(event)
