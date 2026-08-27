from dataclasses import dataclass
from typing import Dict

from app.strategy.config import TIMEFRAME_WEIGHTS


@dataclass(frozen=True)
class MultiTimeframeResult:
    score: float
    bias: str
    confidence: float
    timeframe_scores: Dict[str, float]


class MultiTimeframeEngine:

    def analyze(self, scores: Dict[str, float]) -> MultiTimeframeResult:
        missing = [
            tf for tf in TIMEFRAME_WEIGHTS
            if tf not in scores
        ]

        if missing:
            raise ValueError(
                f"Missing timeframe scores: {missing}"
            )

        for timeframe, score in scores.items():
            if timeframe in TIMEFRAME_WEIGHTS:
                if not -1.0 <= score <= 1.0:
                    raise ValueError(
                        f"{timeframe} score must be between -1 and 1"
                    )

        weighted_score = sum(
            scores[tf] * weight
            for tf, weight in TIMEFRAME_WEIGHTS.items()
        )

        if weighted_score > 0.10:
            bias = "BULLISH"
        elif weighted_score < -0.10:
            bias = "BEARISH"
        else:
            bias = "NEUTRAL"

        confidence = round(
            abs(weighted_score) * 100,
            2,
        )

        return MultiTimeframeResult(
            score=round(weighted_score, 4),
            bias=bias,
            confidence=confidence,
            timeframe_scores=dict(scores),
        )
