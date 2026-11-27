from __future__ import annotations

from math import isfinite
from typing import Any, Mapping

from app.intelligence.council import AgentOpinion, AtlasCouncilCoordinator
from app.intelligence.council_training import CouncilTrainingJournal, PaperTrainingExample
from app.intelligence.executive import AtlasExecutiveAgent


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
) -> dict[str, Any]:
    technical = technical_opinion(signal, snapshot_id=snapshot_id)
    opinions = [technical]

    event = event_opinion(event_state, snapshot_id=snapshot_id)
    if event is not None:
        opinions.append(event)

    confidence = confidence_opinion(
        quality,
        directional_decision=technical.decision,
        snapshot_id=snapshot_id,
    )
    if confidence is not None:
        opinions.append(confidence)

    council = AtlasCouncilCoordinator().build_package(
        symbol=symbol,
        snapshot_id=snapshot_id,
        opinions=opinions,
        senior_risk=senior_risk_assessment(risk),
        data_quality=data_quality,
        agent_profile=agent_profile,
    )
    trade_intent = AtlasExecutiveAgent().decide(council)
    return {"council": council, "trade_intent": trade_intent}


def settled_paper_example(
    *,
    council: Mapping[str, Any],
    trade_intent: Mapping[str, Any],
    realized_direction: str,
) -> PaperTrainingExample:
    if str(trade_intent.get("execution_environment", "")).upper() != "PAPER":
        raise ValueError("Only PAPER trade intents can train ATLAS Council")
    if trade_intent.get("broker_execution_allowed") is not False:
        raise ValueError("Broker-executed intents cannot train ATLAS Council")
    snapshot_id = council.get("snapshot_id")
    if not isinstance(snapshot_id, str) or not snapshot_id.strip() or trade_intent.get("snapshot_id") != snapshot_id:
        raise ValueError("Council and trade intent snapshot_id must match")

    opinions = council.get("opinions") or []
    training_opinions: list[dict[str, Any]] = []
    names = set()
    for opinion in opinions:
        if not isinstance(opinion, Mapping):
            raise ValueError("A settled Council opinion must be an object")
        agent = opinion.get("agent")
        decision = opinion.get("decision")
        confidence = opinion.get("confidence")
        if (
            not isinstance(agent, str) or not agent.strip() or agent.strip() in names
            or decision not in ("BUY", "SELL", "HOLD")
            or isinstance(confidence, bool) or not isinstance(confidence, (int, float))
            or not 0.0 <= confidence <= 1.0
        ):
            raise ValueError("Invalid or duplicate settled Council opinion")
        names.add(agent.strip())
        training_opinions.append(
            {"agent": agent.strip(), "decision": decision, "confidence": float(confidence)}
        )

    return PaperTrainingExample(
        snapshot_id=snapshot_id,
        realized_direction=realized_direction,
        opinions=tuple(training_opinions),
    )


def record_settled_paper_outcome(
    *,
    council: Mapping[str, Any],
    trade_intent: Mapping[str, Any],
    realized_direction: str,
    journal: CouncilTrainingJournal | None = None,
) -> dict[str, Any]:
    example = settled_paper_example(
        council=council, trade_intent=trade_intent, realized_direction=realized_direction,
    )
    return (journal or CouncilTrainingJournal()).append(example)
