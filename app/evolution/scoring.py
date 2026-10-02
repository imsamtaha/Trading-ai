from __future__ import annotations

from math import isfinite

from app.evolution.models import AgentMetrics


METRIC_WEIGHTS = {
    "risk_adjusted_return": 0.30,
    "directional_accuracy": 0.20,
    "calibration": 0.15,
    "drawdown_control": 0.15,
    "regime_accuracy": 0.10,
    "consistency": 0.10,
}


def _unit(value: float) -> float:
    value = float(value)
    if not isfinite(value):
        raise ValueError("Metric values must be finite.")
    return max(0.0, min(1.0, value))


def score_metrics(metrics: AgentMetrics) -> float:
    values = metrics.as_dict()
    score = sum(_unit(values[name]) * weight for name, weight in METRIC_WEIGHTS.items())
    return round(score, 6)

