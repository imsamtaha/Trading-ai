from __future__ import annotations


MIN_AGENT_WEIGHT = 0.30
MAX_AGENT_WEIGHT = 2.50


def bounded_weight(score: float, *, baseline: float = 1.0) -> float:
    """Map a normalized score to a bounded Darwinian influence weight."""
    normalized = max(0.0, min(1.0, float(score)))
    # score=0.5 => baseline. Range remains intentionally conservative.
    adjusted = baseline + ((normalized - 0.5) * 1.4)
    return round(max(MIN_AGENT_WEIGHT, min(MAX_AGENT_WEIGHT, adjusted)), 4)


def normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    cleaned = {
        name: max(MIN_AGENT_WEIGHT, min(MAX_AGENT_WEIGHT, float(value)))
        for name, value in weights.items()
    }
    total = sum(cleaned.values())
    if total <= 0:
        return {}
    return {name: round(value / total, 6) for name, value in cleaned.items()}
