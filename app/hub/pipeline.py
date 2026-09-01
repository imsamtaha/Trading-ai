from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class DecisionResult:
    symbol: str
    action: str
    reason: str
    confidence: float
    approved: bool


def build_mtf_consensus(scan: dict[str, Any]) -> DecisionResult:
    """Conservative MVP decision layer: alignment first, execution later."""
    symbol = str(scan.get("symbol", "")).upper()
    frames = scan.get("timeframes", {})
    errors = scan.get("errors", {})

    if not symbol:
        return DecisionResult("", "WAIT", "missing symbol", 0.0, False)
    if errors or not frames:
        return DecisionResult(symbol, "WAIT", "incomplete market data", 0.0, False)

    directions = []
    for frame in frames.values():
        technical = frame.get("technical", {})
        trend = str(technical.get("trend", "UNKNOWN")).upper()
        if trend in {"BULLISH", "BEARISH"}:
            directions.append(trend)

    if len(directions) != len(frames):
        return DecisionResult(symbol, "WAIT", "insufficient directional confirmation", 0.0, False)

    bullish = directions.count("BULLISH")
    bearish = directions.count("BEARISH")
    total = len(directions)

    if bullish == total:
        return DecisionResult(symbol, "BUY", f"{total}/{total} timeframe alignment", 100.0, True)
    if bearish == total:
        return DecisionResult(symbol, "SELL", f"{total}/{total} timeframe alignment", 100.0, True)

    return DecisionResult(symbol, "WAIT", "timeframe conflict", max(bullish, bearish) / total * 100, False)


def evaluate_scan(scan: dict[str, Any], risk_gate: Callable[[dict[str, Any]], bool] | None = None) -> dict[str, Any]:
    decision = build_mtf_consensus(scan)
    approved = decision.approved
    if approved and risk_gate is not None:
        approved = bool(risk_gate({"symbol": decision.symbol, "action": decision.action}))

    return {
        "symbol": decision.symbol,
        "action": decision.action if approved else "WAIT",
        "confidence": decision.confidence if approved else 0.0,
        "approved": approved,
        "reason": decision.reason if approved else "risk gate rejected or decision not confirmed",
    }
