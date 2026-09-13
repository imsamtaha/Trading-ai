from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping


RegimeClassification = Literal["trending", "range_bound", "high_volatility", "unknown"]


@dataclass(frozen=True)
class TechnicalFeatures:
    returns: list[float]
    volatility: float
    movement_modifier: float
    regime_classification: RegimeClassification
    raw_features: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMContextFeatures:
    sentiment_score: float = 0.0
    event_relevance: float = 0.0
    regime_hint: str = ""
    branch_valid: bool = False


@dataclass(frozen=True)
class MergedFeatureVector:
    features: Mapping[str, Any]

    def to_model_input(self) -> dict[str, Any]:
        return dict(self.features)


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, float(value)))


def merge_features(
    technical: TechnicalFeatures,
    llm_context: LLMContextFeatures | None = None,
    *,
    llm_weight: float = 0.15,
) -> MergedFeatureVector:
    """Merge deterministic and LLM context features for SEAL.

    LLM influence is hard-capped by llm_weight so optional reasoning context can
    enrich the model input without overpowering deterministic market features.
    """
    llm_context = llm_context or LLMContextFeatures()
    capped_weight = _clamp(llm_weight, 0.0, 0.30)
    sentiment = _clamp(llm_context.sentiment_score, -1.0, 1.0)

    merged = {
        "returns": list(technical.returns),
        "volatility": float(technical.volatility),
        "movement_modifier": float(technical.movement_modifier),
        "regime_classification": technical.regime_classification,
        **dict(technical.raw_features),
        "llm_sentiment_score": sentiment,
        "llm_sentiment_weighted": sentiment * capped_weight,
        "llm_event_relevance": _clamp(llm_context.event_relevance, 0.0, 1.0),
        "llm_regime_hint": llm_context.regime_hint,
        "llm_branch_valid": bool(llm_context.branch_valid),
    }
    return MergedFeatureVector(merged)
