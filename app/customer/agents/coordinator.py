from math import isfinite

from app.customer.agents.confidence import calibrate_confidence
from app.customer.contracts import Decision, DecisionCandidate, MarketSnapshot, Signal
from app.customer.realtime.conflict import has_high_impact_news_conflict, usable
from app.customer.realtime.weighting import agent_weight


def coordinate(snapshot: MarketSnapshot, verdicts: list, *, weights: dict[str, float] | None = None) -> DecisionCandidate:
    if any(v.snapshot_id != snapshot.snapshot_id for v in verdicts):
        return DecisionCandidate(snapshot.snapshot_id, snapshot.customer_id, snapshot.account_id, snapshot.mode, Decision.WAIT, 0.0, blockers=("mixed snapshot identity",))
    if has_high_impact_news_conflict(verdicts):
        return DecisionCandidate(snapshot.snapshot_id, snapshot.customer_id, snapshot.account_id, snapshot.mode, Decision.WAIT, 0.0, blockers=("high-impact news conflicts with directional evidence",))
    eligible = [v for v in verdicts if usable(v)]

    def weight(agent: str) -> float:
        baseline = agent_weight(agent)
        if baseline <= 0 or not weights or agent not in weights:
            return baseline
        learned = float(weights[agent])
        return max(0.3, min(2.5, learned)) if isfinite(learned) else baseline

    long_score = sum(weight(v.agent) * v.confidence * float(v.data_quality.get("score", 1.0)) for v in eligible if v.signal is Signal.LONG)
    short_score = sum(weight(v.agent) * v.confidence * float(v.data_quality.get("score", 1.0)) for v in eligible if v.signal is Signal.SHORT)
    if long_score <= 0 and short_score <= 0:
        target, decision = Signal.WAIT, Decision.WAIT
    elif long_score > short_score:
        target, decision = Signal.LONG, Decision.BUY
    elif short_score > long_score:
        target, decision = Signal.SHORT, Decision.SELL
    else:
        target, decision = Signal.WAIT, Decision.WAIT
    confidence = calibrate_confidence(eligible, target) if target in {Signal.LONG, Signal.SHORT} else 0.0
    rationale = (f"weighted_long:{long_score:.4f}", f"weighted_short:{short_score:.4f}")
    return DecisionCandidate(snapshot.snapshot_id, snapshot.customer_id, snapshot.account_id, snapshot.mode, decision, confidence, rationale=rationale)
