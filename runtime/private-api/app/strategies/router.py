from __future__ import annotations

from dataclasses import dataclass

from app.risk.manager import calculate_risk
from app.strategies.models import StrategyCandidate


@dataclass(frozen=True)
class StrategyMode:
    name: str
    min_confidence: float
    active_risk_percent: float
    prime_risk_percent: float


MODES = {
    "CONSERVATIVE": StrategyMode("CONSERVATIVE", 75.0, 0.25, 0.75),
    "BALANCED": StrategyMode("BALANCED", 65.0, 0.35, 0.75),
    "ACTIVE": StrategyMode("ACTIVE", 60.0, 0.25, 0.75),
}


def _classification(score: float) -> tuple[str, str]:
    if score >= 85:
        return "A+", "PRIME"
    if score >= 75:
        return "A", "PRIME"
    if score >= 65:
        return "B+", "ACTIVE"
    if score >= 60:
        return "B", "ACTIVE"
    return "REJECT", "REJECT"


def _regime(technical: dict, structure: dict) -> str:
    trend = str(technical.get("trend", "")).lower()
    market_structure = str(structure.get("structure", "")).lower()
    if trend == "bullish" and market_structure == "bullish":
        return "TRENDING_BULL"
    if trend == "bearish" and market_structure == "bearish":
        return "TRENDING_BEAR"
    if trend in {"sideways", "neutral", "range"}:
        return "RANGE"
    return "TRANSITION"


def _score(technical: dict, structure: dict, direction: str, strategy: str) -> tuple[float, list[str]]:
    score = 40.0
    reasons: list[str] = []
    trend = str(technical.get("trend", "")).lower()
    momentum = str(technical.get("momentum", "")).lower()
    macd = str(technical.get("macd_signal", "")).lower()
    market_structure = str(structure.get("structure", "")).lower()
    desired = "bullish" if direction == "LONG" else "bearish"

    if trend == desired:
        score += 15
        reasons.append("Trend aligned")
    if market_structure == desired:
        score += 20
        reasons.append("Structure aligned")
    if momentum == desired:
        score += 10
        reasons.append("Momentum aligned")
    if macd == desired:
        score += 5
        reasons.append("MACD aligned")

    indicators = technical.get("indicators", {}) or {}
    rsi = indicators.get("rsi_14")
    if isinstance(rsi, (int, float)):
        if direction == "LONG" and 45 <= rsi <= 70:
            score += 5
            reasons.append("RSI supports continuation")
        elif direction == "SHORT" and 30 <= rsi <= 55:
            score += 5
            reasons.append("RSI supports continuation")

    if strategy in {"TREND_PULLBACK", "CONTINUATION_5M"} and trend == desired and market_structure == desired:
        score += 5
        reasons.append("Strategy matches trend regime")

    return min(score, 100.0), reasons


def _choose_strategy(regime: str, technical: dict, structure: dict) -> tuple[str, str] | None:
    trend = str(technical.get("trend", "")).lower()
    market_structure = str(structure.get("structure", "")).lower()

    if regime == "TRENDING_BULL":
        return "CONTINUATION_5M", "LONG"
    if regime == "TRENDING_BEAR":
        return "CONTINUATION_5M", "SHORT"

    # Transition setups require stronger directional agreement from the legacy indicators.
    bullish_votes = sum(v == "bullish" for v in [trend, str(technical.get("momentum", "")).lower(), str(technical.get("macd_signal", "")).lower(), market_structure])
    bearish_votes = sum(v == "bearish" for v in [trend, str(technical.get("momentum", "")).lower(), str(technical.get("macd_signal", "")).lower(), market_structure])
    if bullish_votes >= 3:
        return "LIQUIDITY_RECLAIM", "LONG"
    if bearish_votes >= 3:
        return "LIQUIDITY_RECLAIM", "SHORT"
    return None


def generate_strategy_candidate(
    symbol: str,
    technical: dict,
    structure: dict,
    *,
    mode: str = "BALANCED",
    account_balance: float = 10000.0,
) -> StrategyCandidate | None:
    selected_mode = MODES.get(mode.upper(), MODES["BALANCED"])
    regime = _regime(technical, structure)
    choice = _choose_strategy(regime, technical, structure)
    if choice is None:
        return None

    strategy, direction = choice
    price = technical.get("price")
    atr = (technical.get("indicators", {}) or {}).get("atr_14")
    if not isinstance(price, (int, float)) or not isinstance(atr, (int, float)) or price <= 0 or atr <= 0:
        return None

    # Structural prototype levels: risk engine remains authoritative.
    if direction == "LONG":
        stop_loss = price - (1.25 * atr)
        take_profit = price + (2.5 * atr)
    else:
        stop_loss = price + (1.25 * atr)
        take_profit = price - (2.5 * atr)

    confidence, reasons = _score(technical, structure, direction, strategy)
    classification, lane = _classification(confidence)
    requested_risk = selected_mode.prime_risk_percent if lane == "PRIME" else selected_mode.active_risk_percent

    risk = calculate_risk(
        direction=direction,
        entry=price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        account_balance=account_balance,
        risk_percent=requested_risk,
    )

    qualified = (
        confidence >= selected_mode.min_confidence
        and classification != "REJECT"
        and risk.get("approved", False)
    )

    return StrategyCandidate(
        symbol=symbol,
        strategy=strategy,
        direction=direction,
        regime=regime,
        confidence=round(confidence, 2),
        classification=classification,
        setup_lane=lane,
        entry=float(price),
        stop_loss=float(stop_loss),
        take_profit=float(take_profit),
        risk_reward=float(risk.get("risk_reward", 0.0)),
        qualified=qualified,
        reasons=reasons + [str(risk.get("reason", ""))],
        metadata={"mode": selected_mode.name, "risk": risk},
    )
