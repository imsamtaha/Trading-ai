"""ATLAS trade-gate adapter.

This module converts a deterministic AtlasDecision into the legacy strategy
trade-candidate format. It does not execute trades. It only produces a paper-
trading candidate after the scoring engine, SEAL execution gate, and risk
manager approve.
"""

from __future__ import annotations

from typing import Mapping

from app.intelligence.seal_adapter import ExecutionGatekeeper
from app.risk.manager import calculate_risk

from .engine import AtlasDecision, Bias, DecisionStatus


CONVICTION_CONFIDENCE = {
    "high": 85,
    "moderate": 70,
    "low": 55,
}

PIP_SIZE_BY_ASSET_PREFIX = {
    "XAU": 0.10,
    "XAG": 0.01,
}


def _reject(
    reason: str,
    *,
    decision: AtlasDecision | None = None,
    risk: Mapping | None = None,
    executor: Mapping | None = None,
) -> dict:
    payload = {
        "status": "NO_TRADE",
        "reason": reason,
    }
    if decision is not None:
        payload["atlas_decision"] = decision.to_dict()
    if risk is not None:
        payload["risk"] = dict(risk)
    if executor is not None:
        payload["executor"] = dict(executor)
    return payload


def _pip_size(asset: str) -> float:
    normalized = asset.upper()
    for prefix, size in PIP_SIZE_BY_ASSET_PREFIX.items():
        if normalized.startswith(prefix):
            return size
    if "JPY" in normalized:
        return 0.01
    return 0.0001


def _distance_to_pips(asset: str, distance: float) -> float:
    return abs(distance) / _pip_size(asset)


def atlas_decision_to_signal(decision: AtlasDecision) -> dict:
    """Convert an approved AtlasDecision into the existing signal shape."""
    if decision.status is not DecisionStatus.VALID:
        return {
            "direction": "WAIT",
            "confidence": 0,
            "reason": "ATLAS decision is not valid.",
            "atlas_decision": decision.to_dict(),
        }

    if decision.bias is Bias.LONG:
        direction = "LONG"
    elif decision.bias is Bias.SHORT:
        direction = "SHORT"
    else:
        direction = "WAIT"

    conviction = decision.conviction.value if decision.conviction else "low"

    return {
        "direction": direction,
        "confidence": CONVICTION_CONFIDENCE.get(conviction, 55),
        "conviction": conviction.upper(),
        "long_score": decision.long_score,
        "short_score": decision.short_score,
        "directional_edge": decision.directional_edge,
        "risk_score": decision.risk_score,
        "risk_reward": decision.risk_reward,
        "confluence_count": decision.confluence_count,
        "confluence_factors": list(decision.confluence_factors),
        "atlas_decision": decision.to_dict(),
    }


def _seal_gate_payload(
    *,
    decision: AtlasDecision,
    signal: Mapping,
    stop_loss_pips: float,
    take_profit_pips: float,
) -> dict:
    if decision.bias is Bias.LONG:
        seal_signal = "buy"
    elif decision.bias is Bias.SHORT:
        seal_signal = "sell"
    else:
        seal_signal = "hold"

    return {
        "signal": seal_signal,
        "confidence": float(signal.get("confidence", 0.0)) / 100.0,
        "stop_loss_pips": stop_loss_pips,
        "take_profit_pips": take_profit_pips,
        "supporting_factors": list(decision.confluence_factors),
        "counter_signals": list(decision.veto_reasons),
        "data_quality_concerns": [
            reason
            for reason in decision.veto_reasons
            if "data" in reason or "undefined" in reason
        ],
    }


def create_atlas_trade_candidate(
    *,
    decision: AtlasDecision,
    technical: Mapping,
    account_balance: float = 10_000.0,
    risk_percent: float | None = None,
    stop_atr_multiplier: float = 1.5,
    target_atr_multiplier: float = 3.0,
    execution_gatekeeper: ExecutionGatekeeper | None = None,
    market_context: Mapping | None = None,
) -> dict:
    """Gate an AtlasDecision into a risk-approved trade candidate.

    Requirements:
    - ATLAS status must be VALID.
    - Bias must be LONG or SHORT.
    - Current price and ATR must be available.
    - SEAL execution gate must approve confirmation quality and stop/target.
    - Risk manager must approve direction, stop, target, and R:R.
    - Account risk remains capped by the risk manager at 2%.
    """
    if decision.status is not DecisionStatus.VALID:
        return _reject("ATLAS decision is not valid.", decision=decision)

    if decision.bias not in {Bias.LONG, Bias.SHORT}:
        return _reject("ATLAS bias is neutral.", decision=decision)

    if decision.risk_reward is None or decision.risk_reward < 1.5:
        return _reject("ATLAS risk/reward is below the minimum 1.5:1.", decision=decision)

    price = technical.get("price")
    atr = (technical.get("indicators") or {}).get("atr_14")

    if price is None or atr is None:
        return _reject("Insufficient price or ATR data.", decision=decision)

    price = float(price)
    atr = float(atr)

    if price <= 0 or atr <= 0:
        return _reject("Invalid price or ATR data.", decision=decision)

    direction = "LONG" if decision.bias is Bias.LONG else "SHORT"

    if direction == "LONG":
        stop_loss = price - (stop_atr_multiplier * atr)
        take_profit = price + (target_atr_multiplier * atr)
    else:
        stop_loss = price + (stop_atr_multiplier * atr)
        take_profit = price - (target_atr_multiplier * atr)

    signal = atlas_decision_to_signal(decision)
    stop_loss_pips = _distance_to_pips(decision.asset, price - stop_loss)
    take_profit_pips = _distance_to_pips(decision.asset, take_profit - price)
    gatekeeper = execution_gatekeeper or ExecutionGatekeeper()
    executor = gatekeeper.evaluate(
        _seal_gate_payload(
            decision=decision,
            signal=signal,
            stop_loss_pips=stop_loss_pips,
            take_profit_pips=take_profit_pips,
        ),
        market_context=market_context,
    )

    if executor["executor_decision"] != "APPROVE_EXECUTION":
        return _reject(executor["executor_reason"], decision=decision, executor=executor)

    risk_kwargs = {
        "direction": direction,
        "entry": price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "account_balance": account_balance,
    }
    if risk_percent is not None:
        risk_kwargs["risk_percent"] = risk_percent

    risk = calculate_risk(**risk_kwargs)

    if not risk["approved"]:
        return _reject(risk["reason"], decision=decision, risk=risk, executor=executor)

    return {
        "status": "TRADE_CANDIDATE",
        "source": "ATLAS_SEAL",
        "direction": direction,
        "confidence": signal["confidence"],
        "conviction": signal["conviction"],
        "entry": price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "stop_loss_pips": stop_loss_pips,
        "take_profit_pips": take_profit_pips,
        "signal": signal,
        "executor": executor,
        "risk": risk,
        "atlas_decision": decision.to_dict(),
    }
