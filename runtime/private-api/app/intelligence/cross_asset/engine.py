from dataclasses import dataclass


@dataclass
class AssetSignal:
    asset: str
    direction: str
    strength: float
    source: str


class CrossAssetEngine:

    DIRECTIONS = {
        "BULLISH",
        "BEARISH",
        "NEUTRAL",
    }

    def __init__(self):
        self.signals = []

    def add_signal(
        self,
        asset,
        direction,
        strength,
        source="market",
    ):

        direction = direction.upper()

        if direction not in self.DIRECTIONS:
            raise ValueError(
                f"Invalid direction: {direction}"
            )

        strength = max(
            0.0,
            min(1.0, float(strength))
        )

        signal = AssetSignal(
            asset=asset,
            direction=direction,
            strength=strength,
            source=source,
        )

        self.signals.append(signal)

        return signal

    def directional_score(self):

        if not self.signals:
            return 0.0

        scores = []

        for signal in self.signals:

            if signal.direction == "BULLISH":
                value = signal.strength

            elif signal.direction == "BEARISH":
                value = -signal.strength

            else:
                value = 0.0

            scores.append(value)

        return sum(scores) / len(scores)

    def detect_conflicts(self):

        bullish = [
            signal
            for signal in self.signals
            if signal.direction == "BULLISH"
        ]

        bearish = [
            signal
            for signal in self.signals
            if signal.direction == "BEARISH"
        ]

        bullish_strength = sum(
            signal.strength
            for signal in bullish
        )

        bearish_strength = sum(
            signal.strength
            for signal in bearish
        )

        total_strength = (
            bullish_strength
            + bearish_strength
        )

        if total_strength == 0:
            conflict_score = 0.0
        else:
            conflict_score = (
                min(
                    bullish_strength,
                    bearish_strength,
                )
                / total_strength
            )

        if conflict_score >= 0.35:
            level = "HIGH"

        elif conflict_score >= 0.20:
            level = "MEDIUM"

        else:
            level = "LOW"

        return {
            "conflict_score": round(
                conflict_score,
                3,
            ),
            "conflict_level": level,
            "bullish_strength": round(
                bullish_strength,
                3,
            ),
            "bearish_strength": round(
                bearish_strength,
                3,
            ),
        }

    def analyze(self):

        score = self.directional_score()
        conflicts = self.detect_conflicts()

        if score >= 0.20:
            bias = "BULLISH"

        elif score <= -0.20:
            bias = "BEARISH"

        else:
            bias = "NEUTRAL"

        return {
            "bias": bias,
            "directional_score": round(
                score,
                3,
            ),
            "signal_count": len(
                self.signals
            ),
            "conflicts": conflicts,
            "signals": [
                signal.__dict__
                for signal in self.signals
            ],
        }


if __name__ == "__main__":

    engine = CrossAssetEngine()

    # Example market context.
    # These are synthetic test values,
    # not live market data.

    engine.add_signal(
        "BTC",
        "BULLISH",
        0.80,
        "technical",
    )

    engine.add_signal(
        "USD",
        "BEARISH",
        0.70,
        "macro",
    )

    engine.add_signal(
        "GOLD",
        "BULLISH",
        0.60,
        "macro",
    )

    engine.add_signal(
        "YIELDS",
        "BEARISH",
        0.75,
        "macro",
    )

    result = engine.analyze()

    print()
    print(
        "CROSS-ASSET INTELLIGENCE TEST"
    )
    print("=" * 50)

    print(
        "Bias:",
        result["bias"],
    )

    print(
        "Directional Score:",
        result["directional_score"],
    )

    print(
        "Conflicts:",
        result["conflicts"],
    )

    print(
        "Signals:",
        result["signals"],
    )
