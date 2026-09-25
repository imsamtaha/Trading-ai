DEFAULT_AGENT_WEIGHTS = {
    "technical": 1.25,
    "regime": 1.1,
    "news": 1.2,
    "sentiment": 0.9,
    "financial": 0.0,
    "system_watchdog": 0.0,
}


def agent_weight(agent: str) -> float:
    return DEFAULT_AGENT_WEIGHTS.get(agent, 1.0)
