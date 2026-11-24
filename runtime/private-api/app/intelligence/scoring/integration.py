"""Normalize deterministic analysis outputs into ATLAS scoring inputs.

This layer deliberately avoids fabricating unavailable evidence. Missing or
non-directional observations are mapped to 0.0 and remain neutral.
"""

from __future__ import annotations

from typing import Mapping

from .engine import AtlasScoringEngine, Regime, RiskFlags, ScoringInput


def _clamp(value: float) -> float:
    return max(-1.0, min(1.0, float(value)))


def _direction(label: str | None) -> float:
    normalized = (label or "").strip().lower()
    if normalized in {"bullish", "bull", "long"}:
        return 1.0
    if normalized in {"bearish", "bear", "short"}:
        return -1.0
    return 0.0


def _regime_from_analysis(regime_analysis: Mapping | None) -> Regime:
    primary = str((regime_analysis or {}).get("primary_regime", "")).upper()
    mapping = {
        "BULL_TREND": Regime.TRENDING_BULL,
        "BEAR_TREND": Regime.TRENDING_BEAR,
        "RANGE": Regime.RANGE_BOUND,
        "HIGH_VOLATILITY": Regime.HIGH_VOLATILITY,
        "LOW_VOLATILITY": Regime.LOW_VOLATILITY,
    }
    return mapping.get(primary, Regime.UNKNOWN)


def _structure_evidence(structure_analysis: Mapping | None) -> float:
    analysis = structure_analysis or {}
    base = _direction(analysis.get("structure"))

    events = analysis.get("break_events") or []
    for event in events:
        event_type = str(event.get("type", "")).upper()
        if event_type == "BOS_BULLISH":
            base = max(base, 1.0)
        elif event_type == "BOS_BEARISH":
            base = min(base, -1.0)

    return _clamp(base)


def _liquidity_evidence(structure_analysis: Mapping | None) -> float:
    score = 0.0
    for event in (structure_analysis or {}).get("liquidity_events") or []:
        event_type = str(event.get("type", "")).upper()
        if event_type == "LIQUIDITY_SWEEP_LOW":
            score += 0.5
        elif event_type == "LIQUIDITY_SWEEP_HIGH":
            score -= 0.5
    return _clamp(score)


def _momentum_evidence(technical_analysis: Mapping | None) -> float:
    technical = technical_analysis or {}
    momentum = str(technical.get("momentum", "")).lower()
    macd_signal = str(technical.get("macd_signal", "")).lower()

    score = 0.0
    if momentum == "bullish":
        score += 0.5
    elif momentum == "bearish":
        score -= 0.5
    # Overbought/oversold are conditions, not directional entries by themselves.

    if macd_signal == "bullish":
        score += 0.5
    elif macd_signal == "bearish":
        score -= 0.5

    return _clamp(score)


def _support_resistance_evidence(technical_analysis: Mapping | None) -> float:
    technical = technical_analysis or {}
    levels = technical.get("levels") or {}
    indicators = technical.get("indicators") or {}
    price = technical.get("price")
    support = levels.get("support")
    resistance = levels.get("resistance")
    atr = indicators.get("atr_14")

    if None in {price, support, resistance, atr} or float(atr) <= 0:
        return 0.0

    price = float(price)
    support = float(support)
    resistance = float(resistance)
    atr = float(atr)

    if abs(price - support) <= atr:
        return 0.5
    if abs(resistance - price) <= atr:
        return -0.5
    return 0.0


def _trend_evidence(
    technical_analysis: Mapping | None,
    regime_analysis: Mapping | None,
    mtf_trends: Mapping[str, str] | None,
) -> float:
    if mtf_trends:
        # Higher timeframes receive more weight. Unknown labels stay neutral.
        weights = {"5m": 1, "15m": 1, "30m": 2, "1h": 3, "4h": 4, "1d": 5, "1w": 6}
        weighted_sum = 0.0
        weight_total = 0.0
        for timeframe, label in mtf_trends.items():
            weight = float(weights.get(str(timeframe).lower(), 1))
            direction = _direction(label)
            if direction == 0:
                continue
            weighted_sum += direction * weight
            weight_total += weight
        if weight_total:
            return _clamp(weighted_sum / weight_total)

    technical_direction = _direction((technical_analysis or {}).get("trend"))
    raw_state = (regime_analysis or {}).get("raw_state") or {}
    regime_trend_score = raw_state.get("trend_score")

    if regime_trend_score is None:
        return technical_direction
    if technical_direction == 0:
        return _clamp(regime_trend_score)
    return _clamp((technical_direction + _clamp(regime_trend_score)) / 2.0)


def _volume_evidence(technical_analysis: Mapping | None, trend_evidence: float) -> float:
    technical = technical_analysis or {}
    if str(technical.get("volume_state", "")).lower() != "high":
        return 0.0
    # High volume confirms the observed directional trend; it is not directional alone.
    if trend_evidence > 0:
        return 0.5
    if trend_evidence < 0:
        return -0.5
    return 0.0


def _price_action_evidence(structure_analysis: Mapping | None) -> float:
    score = 0.0
    for event in (structure_analysis or {}).get("break_events") or []:
        event_type = str(event.get("type", "")).upper()
        if event_type == "BOS_BULLISH":
            score += 1.0
        elif event_type == "BOS_BEARISH":
            score -= 1.0
    return _clamp(score)


def _merge_flags(base: RiskFlags | None, *, extreme_volatility: bool, major_event: bool) -> RiskFlags:
    base = base or RiskFlags()
    return RiskFlags(
        data_stale=base.data_stale,
        critical_data_missing=base.critical_data_missing,
        invalidation_undefined=base.invalidation_undefined,
        extreme_volatility=base.extreme_volatility or extreme_volatility,
        major_event_imminent=base.major_event_imminent or major_event,
        chasing_entry=base.chasing_entry,
        higher_timeframe_conflict=base.higher_timeframe_conflict,
        excessive_account_risk=base.excessive_account_risk,
    )


def build_scoring_input(
    *,
    asset: str,
    timeframe: str,
    technical_analysis: Mapping,
    structure_analysis: Mapping,
    regime_analysis: Mapping,
    risk_reward: float | None,
    account_risk_fraction: float = 0.01,
    risk_score: float | None = None,
    risk_flags: RiskFlags | None = None,
    mtf_trends: Mapping[str, str] | None = None,
    macro_evidence: float = 0.0,
) -> ScoringInput:
    """Build a validated ScoringInput from existing deterministic engines."""
    trend = _trend_evidence(technical_analysis, regime_analysis, mtf_trends)
    primary = str((regime_analysis or {}).get("primary_regime", "")).upper()
    raw_state = (regime_analysis or {}).get("raw_state") or {}

    derived_risk_score = risk_score
    if derived_risk_score is None:
        volatility = abs(float(raw_state.get("volatility_score", 0.0)))
        event = max(0.0, float(raw_state.get("event_risk_score", 0.0)))
        derived_risk_score = min(100.0, max(volatility, event) * 100.0)

    flags = _merge_flags(
        risk_flags,
        extreme_volatility=primary == "HIGH_VOLATILITY",
        major_event=primary == "EVENT_DRIVEN",
    )

    factors = {
        "structure": _structure_evidence(structure_analysis),
        "trend_mtf": trend,
        "support_resistance": _support_resistance_evidence(technical_analysis),
        "liquidity": _liquidity_evidence(structure_analysis),
        "momentum": _momentum_evidence(technical_analysis),
        "volume": _volume_evidence(technical_analysis, trend),
        # Volatility is not directional evidence. It belongs in risk gating.
        "volatility": 0.0,
        "price_action": _price_action_evidence(structure_analysis),
        "macro": _clamp(macro_evidence),
    }

    return ScoringInput(
        asset=asset,
        timeframe=timeframe,
        regime=_regime_from_analysis(regime_analysis),
        factors=factors,
        risk_score=float(derived_risk_score),
        risk_reward=risk_reward,
        account_risk_fraction=account_risk_fraction,
        risk_flags=flags,
    )


def score_analysis(**kwargs):
    """Convenience entry point: normalize analysis outputs and score them."""
    return AtlasScoringEngine().score(build_scoring_input(**kwargs))
