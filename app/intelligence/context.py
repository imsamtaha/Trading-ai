from __future__ import annotations

from typing import Any


DIRECTION_VALUES = {
    "LONG": 1.0,
    "BULLISH": 1.0,
    "BUY": 1.0,
    "SHORT": -1.0,
    "BEARISH": -1.0,
    "SELL": -1.0,
    "WAIT": 0.0,
    "NEUTRAL": 0.0,
    "UNKNOWN": 0.0,
}


def direction_value(value: Any) -> float:
    return DIRECTION_VALUES.get(str(value).upper(), 0.0)


def weighted_score(values: dict[str, float], weights: dict[str, float]) -> float:
    total_weight = sum(weights.get(tf, 0.0) for tf in values)
    if total_weight <= 0:
        return 0.0
    return sum(values[tf] * weights.get(tf, 0.0) for tf in values) / total_weight


def build_mtf_context(results: dict[str, dict], weights: dict[str, float]) -> dict:
    """Derive deterministic context from validated MT5 timeframe results.

    Macro, news, geopolitical and external cross-asset feeds remain separate
    providers; this layer never fabricates those values.
    """
    trend = {tf: direction_value(item["technical"].get("trend")) for tf, item in results.items()}
    momentum = {tf: direction_value(item["technical"].get("momentum")) for tf, item in results.items()}
    macd = {tf: direction_value(item["technical"].get("macd_signal")) for tf, item in results.items()}
    structure = {tf: direction_value(item["structure"].get("structure")) for tf, item in results.items()}
    signal = {
        tf: max(-1.0, min(1.0, (float(item["signal"].get("score", 50)) - 50.0) / 50.0))
        for tf, item in results.items()
    }

    mtf_score = weighted_score(signal, weights)
    trend_score = weighted_score(trend, weights)
    momentum_score = weighted_score(momentum, weights)
    macd_score = weighted_score(macd, weights)
    structure_score = weighted_score(structure, weights)

    evidence = [mtf_score, trend_score, momentum_score, macd_score, structure_score]
    directional = sum(evidence) / len(evidence)
    dispersion = sum(abs(value - directional) for value in evidence) / len(evidence)
    conflict = min(1.0, dispersion)

    if directional >= 0.45:
        bias = "BULLISH"
    elif directional <= -0.45:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    return {
        "bias": bias,
        "directional_score": round(directional, 4),
        "mtf_score": round(mtf_score, 4),
        "trend_score": round(trend_score, 4),
        "momentum_score": round(momentum_score, 4),
        "macd_score": round(macd_score, 4),
        "structure_score": round(structure_score, 4),
        "conflict_score": round(conflict, 4),
        "evidence": {
            "signal": signal,
            "trend": trend,
            "momentum": momentum,
            "macd": macd,
            "structure": structure,
        },
    }
