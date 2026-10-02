from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from threading import RLock

from app.evolution.models import AgentMetrics, EvolutionDecision
from app.evolution.scoring import score_metrics
from app.evolution.weights import bounded_weight, normalize_weights


@dataclass
class EvolutionEngine:
    """Shadow prompt evaluator; no broker or execution dependencies."""

    min_improvement: float = 0.03
    agent_scores: dict[str, float] = field(default_factory=dict)
    agent_weights: dict[str, float] = field(default_factory=dict)
    active_prompts: dict[str, str] = field(default_factory=dict)
    agent_versions: dict[str, int] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False, compare=False)

    def __post_init__(self):
        if not isfinite(self.min_improvement) or self.min_improvement <= 0:
            raise ValueError("min_improvement must be finite and positive.")

    def record(self, agent: str, metrics: AgentMetrics) -> dict:
        score = score_metrics(metrics)
        with self._lock:
            self.agent_scores[agent] = score
            self.agent_weights[agent] = bounded_weight(score)
            self.agent_versions[agent] = self.agent_versions.get(agent, 0) + 1
            return {
                "score": score,
                "raw_weight": self.agent_weights[agent],
                "version": self.agent_versions[agent],
                "normalized_weights": self.normalized_weights(),
            }

    def normalized_weights(self) -> dict[str, float]:
        with self._lock:
            return normalize_weights(self.agent_weights)

    def worst_agent(self) -> str | None:
        with self._lock:
            return min(self.agent_scores, key=self.agent_scores.get) if self.agent_scores else None

    def evaluate_candidate(
        self, *, agent: str, incumbent_metrics: AgentMetrics,
        candidate_metrics: AgentMetrics, candidate_prompt: str,
        expected_version: int | None = None,
    ) -> EvolutionDecision:
        supplied_incumbent = score_metrics(incumbent_metrics)
        candidate = score_metrics(candidate_metrics)
        with self._lock:
            version = self.agent_versions.get(agent, 0)
            if expected_version is not None and expected_version != version:
                raise ValueError("Incumbent version changed; reevaluate the candidate.")
            incumbent = self.agent_scores.get(agent, supplied_incumbent)
            # Both scores have six-decimal precision. Compare at that precision.
            improvement = round(candidate - incumbent, 6)
            if improvement >= self.min_improvement:
                self.active_prompts[agent] = candidate_prompt
                self.agent_scores[agent] = candidate
                self.agent_weights[agent] = bounded_weight(candidate)
                self.agent_versions[agent] = version + 1
                return EvolutionDecision(
                    agent=agent, incumbent_score=incumbent, candidate_score=candidate,
                    action="PROMOTE", reason=f"Candidate improved composite score by {improvement:.6f}.",
                    promoted_prompt=candidate_prompt,
                )
            return EvolutionDecision(
                agent=agent, incumbent_score=incumbent, candidate_score=candidate,
                action="REVERT", reason=f"Candidate improvement {improvement:.6f} is below required threshold {self.min_improvement:.6f}.",
            )

    def status(self) -> dict:
        with self._lock:
            return {
                "mode": "shadow_evolution", "execution_access": False,
                "min_improvement": self.min_improvement,
                "worst_agent": self.worst_agent(), "scores": dict(self.agent_scores),
                "weights": self.normalized_weights(), "versions": dict(self.agent_versions),
                "active_prompt_agents": sorted(self.active_prompts),
            }
