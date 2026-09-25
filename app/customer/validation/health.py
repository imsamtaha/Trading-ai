from __future__ import annotations

import json
from pathlib import Path


class AgentHealthTracker:
    def __init__(self, path):
        self.path = Path(path)
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.data = {}

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, sort_keys=True), encoding="utf-8")

    def update(self, agent: str, *, stale: bool, error: bool, latency_ms: float) -> float:
        previous = float(self.data.get(agent, 1.0))
        penalty = (0.2 if stale else 0.0) + (0.3 if error else 0.0) + (0.2 if latency_ms >= 1000 else 0.0)
        recovery = 0.03 if penalty == 0 else 0.0
        score = max(0.0, min(1.0, previous - penalty + recovery))
        self.data[agent] = round(score, 4)
        self._save()
        return self.data[agent]

    def score(self, agent: str) -> float:
        return float(self.data.get(agent, 1.0))


def scenario_flags(
    snapshot,
    *,
    mt5_connected: bool,
    duplicate_signal: bool,
    conflicting_agents: bool,
    rapid_drawdown_pct: float,
    high_impact_news: bool,
) -> set[str]:
    flags: set[str] = set()
    if float(snapshot.market.get("spread_points", 0.0) or 0.0) >= 50:
        flags.add("spread_spike")
    if float(snapshot.market.get("volatility", 0.0) or 0.0) >= 1.5:
        flags.add("volatility_spike")
    if abs(float(snapshot.market.get("gap_pct", 0.0) or 0.0)) >= 1.0:
        flags.add("gap")
    if not mt5_connected:
        flags.add("mt5_disconnect")
    if duplicate_signal:
        flags.add("duplicate_signal")
    if conflicting_agents:
        flags.add("conflicting_agents")
    if rapid_drawdown_pct >= 3.0:
        flags.add("rapid_drawdown")
    if high_impact_news:
        flags.add("high_impact_news")
    return flags
