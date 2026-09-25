from app.customer.contracts import AgentStatus, AgentVerdict


def usable(verdict: AgentVerdict) -> bool:
    return (
        verdict.status is AgentStatus.OK
        and verdict.data_quality.get("fresh") is True
        and not verdict.blockers
    )


def has_high_impact_news_conflict(verdicts: list[AgentVerdict]) -> bool:
    news = [v for v in verdicts if v.agent == "news" and usable(v)]
    if not news:
        return False
    high = [v for v in news if any(str(e).lower() == "impact:high" for e in v.evidence)]
    if not high:
        return False
    directional = {v.signal.value for v in verdicts if usable(v) and v.signal.value in {"LONG", "SHORT"}}
    return len(directional) > 1
