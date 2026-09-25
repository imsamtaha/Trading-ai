from app.customer.contracts import AgentVerdict, Signal
from app.customer.realtime.conflict import usable


def calibrate_confidence(verdicts: list[AgentVerdict], target_signal: Signal) -> float:
    aligned = [v for v in verdicts if usable(v) and v.signal is target_signal]
    if not aligned:
        return 0.0
    agents = {v.agent for v in aligned}
    mean = sum(v.confidence * float(v.data_quality.get("score", 1.0)) for v in aligned) / len(aligned)
    diversity = min(1.0, 0.55 + 0.15 * len(agents))
    concentration_penalty = 0.85 if len({e for v in aligned for e in v.evidence}) <= 1 else 1.0
    return round(max(0.0, min(1.0, mean * diversity * concentration_penalty)), 4)
