from __future__ import annotations

from math import isfinite
from typing import Any, Mapping

from app.intelligence.council import AgentOpinion, AtlasCouncilCoordinator
from app.intelligence.council_training import CouncilTrainingJournal, PaperTrainingExample
from app.intelligence.executive import AtlasExecutiveAgent
from app.intelligence.specialists import MacroAnalyst, QuantitativeStrategist, RiskExecutive, specialist_contracts


def _confidence(value: Any) -> float:
    score = float(value)
    if not isfinite(score):
        raise ValueError("confidence must be finite")
    if score > 1.0:
        score /= 100.0
    if not 0.0 <= score <= 1.0:
        raise ValueError("confidence must be between 0 and 1")
    return score


def technical_opinion(signal: Mapping[str, Any], *, snapshot_id: str) -> AgentOpinion:
    direction = str(signal.get("direction", "WAIT")).upper()
    decision = {"LONG": "BUY", "SHORT": "SELL"}.get(direction, "HOLD")
    confidence = _confidence(signal.get("confidence", 0.0))
    reasons = signal.get("reasons") or ()
    evidence = tuple(str(item) for item in reasons[:8]) if isinstance(reasons, (list, tuple)) else ()
    return AgentOpinion(
        agent="technical",
        decision=decision,
        confidence=confidence,
        evidence=evidence,
        snapshot_id=snapshot_id,
    )


def event_opinion(event_state: Mapping[str, Any] | None, *, snapshot_id: str) -> AgentOpinion | None:
    if not event_state:
        return None
    bias = str(event_state.get("market_bias", "NEUTRAL")).upper()
    decision = {"BULLISH": "BUY", "BEARISH": "SELL"}.get(bias, "HOLD")
    confidence = _confidence(event_state.get("confidence", 0.0))
    risk_level = str(event_state.get("risk_level", "UNKNOWN"))
    evidence = (f"event_risk={risk_level}",)
    return AgentOpinion(
        agent="event_intelligence",
        decision=decision,
        confidence=confidence,
        evidence=evidence,
        snapshot_id=snapshot_id,
    )


def confidence_opinion(
    quality: Mapping[str, Any] | None,
    *,
    directional_decision: str,
    snapshot_id: str,
) -> AgentOpinion | None:
    if not quality:
        return None
    confidence = _confidence(quality.get("execution_confidence", 0.0))
    directional = directional_decision.upper()
    if directional not in {"BUY", "SELL"} or confidence < 0.35:
        decision = "HOLD"
    else:
        decision = directional
    evidence = (
        f"signal_quality={quality.get('signal_quality', 'UNKNOWN')}",
        f"evidence_quality={quality.get('evidence_quality', 'UNKNOWN')}",
    )
    return AgentOpinion(
        agent="confidence",
        decision=decision,
        confidence=confidence,
        evidence=evidence,
        snapshot_id=snapshot_id,
    )


def senior_risk_assessment(risk: Mapping[str, Any]) -> dict[str, Any]:
    approved = risk.get("approved") is True
    return {
        "agent": "Senior Risk Management Agent",
        "assessment": "RISK_ACCEPTABLE" if approved else "RISK_REJECT",
        "reason": str(risk.get("reason", "Risk result unavailable.")),
    }


def build_paper_council(
    *,
    symbol: str,
    snapshot_id: str,
    signal: Mapping[str, Any],
    risk: Mapping[str, Any],
    data_quality: float,
    event_state: Mapping[str, Any] | None = None,
    quality: Mapping[str, Any] | None = None,
    agent_profile: Mapping[str, Any] | None = None,
    recovery: Mapping[str, Any] | None = None,
    macro_state: Mapping[str, Any] | None = None,
    open_symbols: tuple[str, ...] | list[str] = (),
    correlation: Mapping[str, Any] | None = None,
    as_of: str | None = None,
) -> dict[str, Any]:
    quant, quant_info = QuantitativeStrategist().evaluate(signal, quality, snapshot_id=snapshot_id)
    macro, macro_info = MacroAnalyst().evaluate(macro_state, symbol=symbol, snapshot_id=snapshot_id, as_of=as_of)
    opinions = [quant, macro]
    risk_verdict = RiskExecutive().assess(risk, symbol=symbol, snapshot_id=snapshot_id,
                                         open_symbols=open_symbols, correlation=correlation, as_of=as_of)

    if recovery is not None:
        opinions.append(AgentOpinion(agent="recovery_guardian", decision="HOLD",
            confidence=0.0, evidence=tuple(recovery.get("reason_codes") or ()), snapshot_id=snapshot_id))

    council = AtlasCouncilCoordinator().build_package(
        symbol=symbol,
        snapshot_id=snapshot_id,
        opinions=opinions,
        senior_risk=senior_risk_assessment(risk),
        data_quality=data_quality,
        agent_profile=agent_profile,
    )
    if recovery is not None:
        council["recovery_guardian"] = dict(recovery)
    council["specialist_schema_version"] = 1
    council["specialists"] = {"macro_analyst": macro_info, "quantitative_strategist": quant_info,
                               "risk_executive": specialist_contracts()["risk_executive"]}
    council["risk_executive"] = risk_verdict
    # News and signal-quality tools provide context, not extra directional votes.
    council["event_context"] = dict(event_state) if event_state else None
    trade_intent = AtlasExecutiveAgent().decide(council)
    return {"council": council, "trade_intent": trade_intent}


def record_settled_paper_outcome(
    *,
    council: Mapping[str, Any],
    trade_intent: Mapping[str, Any],
    realized_direction: str,
    journal: CouncilTrainingJournal | None = None,
) -> dict[str, Any]:
    if str(trade_intent.get("execution_environment", "")).upper() != "PAPER":
        raise ValueError("Only PAPER trade intents can train ATLAS Council")
    if bool(trade_intent.get("broker_execution_allowed", True)):
        raise ValueError("Broker-executed intents cannot train ATLAS Council")
    if trade_intent.get("snapshot_id") != council.get("snapshot_id"):
        raise ValueError("Council and trade intent snapshot_id must match")

    opinions = council.get("opinions") or []
    training_opinions: list[dict[str, Any]] = []
    for opinion in opinions:
        if not isinstance(opinion, Mapping) or opinion.get("agent") in {"recovery_guardian", "risk_executive", "macro_analyst"}:
            continue  # A veto supervisor has no directional prediction to score.
        training_opinions.append(
            {
                "agent": str(opinion.get("agent", "")),
                "decision": str(opinion.get("decision", "")),
                "confidence": float(opinion.get("confidence", 0.0)),
            }
        )

    example = PaperTrainingExample(
        snapshot_id=str(council.get("snapshot_id", "")),
        realized_direction=realized_direction,
        opinions=tuple(training_opinions),
    )
    return (journal or CouncilTrainingJournal()).append(example)
