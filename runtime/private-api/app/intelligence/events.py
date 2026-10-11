from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List


@dataclass
class MarketEvent:
    title: str
    category: str
    source: str
    timestamp: str

    impact: float = 0.0
    surprise: float = 0.0
    risk: float = 0.0

    affected_assets: List[str] = field(
        default_factory=list
    )

    sentiment: str = "NEUTRAL"
    confidence: float = 0.0

    verified: bool = False


class EventIntelligence:

    CATEGORIES = {
        "FED",
        "MACRO",
        "POLITICAL",
        "GEOPOLITICAL",
        "CRYPTO",
        "GOLD",
        "FX",
        "OTHER",
    }

    SENTIMENTS = {
        "BULLISH",
        "BEARISH",
        "NEUTRAL",
    }

    def __init__(self):
        self.events = []

    def add_event(self, event: MarketEvent):

        if event.category not in self.CATEGORIES:
            raise ValueError(
                f"Unsupported category: "
                f"{event.category}"
            )

        if event.sentiment not in self.SENTIMENTS:
            raise ValueError(
                f"Unsupported sentiment: "
                f"{event.sentiment}"
            )

        event.impact = self._clamp(
            event.impact
        )

        event.surprise = self._clamp(
            event.surprise
        )

        event.risk = self._clamp(
            event.risk
        )

        event.confidence = self._clamp(
            event.confidence
        )

        self.events.append(event)

        return event

    def _clamp(self, value):

        return max(
            0.0,
            min(1.0, float(value))
        )

    def analyze_event(self, event):

        if not event.verified:

            confidence = min(
                event.confidence,
                0.40,
            )

        else:
            confidence = event.confidence

        severity = (
            event.impact
            * 0.45
            + event.surprise
            * 0.25
            + event.risk
            * 0.30
        )

        if event.sentiment == "BULLISH":
            directional_score = severity

        elif event.sentiment == "BEARISH":
            directional_score = -severity

        else:
            directional_score = 0.0

        return {
            "title": event.title,
            "category": event.category,
            "source": event.source,
            "timestamp": event.timestamp,
            "sentiment": event.sentiment,
            "severity": round(
                severity,
                3,
            ),
            "directional_score": round(
                directional_score,
                3,
            ),
            "confidence": round(
                confidence,
                3,
            ),
            "verified": event.verified,
            "affected_assets":
                event.affected_assets,
        }

    def market_state(self):

        if not self.events:

            return {
                "event_count": 0,
                "market_bias": "NEUTRAL",
                "risk_level": "LOW",
                "confidence": 0.0,
                "events": [],
            }

        analyzed = [
            self.analyze_event(event)
            for event in self.events
        ]

        weighted_scores = []

        for item in analyzed:

            weighted_scores.append(
                item["directional_score"]
                * item["confidence"]
            )

        average_score = (
            sum(weighted_scores)
            / len(weighted_scores)
        )

        average_risk = sum(
            event.risk
            for event in self.events
        ) / len(self.events)

        average_confidence = sum(
            event.confidence
            for event in self.events
        ) / len(self.events)

        if average_score > 0.15:
            bias = "BULLISH"

        elif average_score < -0.15:
            bias = "BEARISH"

        else:
            bias = "NEUTRAL"

        if average_risk >= 0.75:
            risk_level = "EXTREME"

        elif average_risk >= 0.50:
            risk_level = "HIGH"

        elif average_risk >= 0.25:
            risk_level = "MEDIUM"

        else:
            risk_level = "LOW"

        return {
            "event_count": len(
                self.events
            ),
            "market_bias": bias,
            "risk_level": risk_level,
            "directional_score": round(
                average_score,
                3,
            ),
            "confidence": round(
                average_confidence,
                3,
            ),
            "events": analyzed,
        }


def create_event(
    title,
    category,
    source,
    sentiment="NEUTRAL",
    impact=0.0,
    surprise=0.0,
    risk=0.0,
    confidence=0.0,
    verified=False,
    affected_assets=None,
):

    event = MarketEvent(
        title=title,
        category=category,
        source=source,
        timestamp=datetime.now(
            timezone.utc
        ).isoformat(),
        sentiment=sentiment,
        impact=impact,
        surprise=surprise,
        risk=risk,
        confidence=confidence,
        verified=verified,
        affected_assets=(
            affected_assets or []
        ),
    )

    return event


if __name__ == "__main__":

    intelligence = EventIntelligence()

    event = create_event(
        title="Major central bank statement",
        category="FED",
        source="official",
        sentiment="BEARISH",
        impact=0.90,
        surprise=0.80,
        risk=0.85,
        confidence=0.95,
        verified=True,
        affected_assets=[
            "BTCUSDT",
            "XAUUSD",
            "USD",
        ],
    )

    intelligence.add_event(event)

    print()
    print(
        "EVENT INTELLIGENCE TEST"
    )
    print("=" * 40)

    print(
        intelligence.market_state()
    )
