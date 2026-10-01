from __future__ import annotations

from dataclasses import dataclass, field

from app.evolution.models import AgentMetrics, EvolutionDecision
from app.evolution.scoring import score_metrics
from app.evolution.weights import bounded_weight, normalize_weights


@dataclass
class EvolutionEngine:
    """GIC-style evaluator for ATLAS specialist agents.

    Important boundary: this class has no broker dependency and no execution
    method. It may evolve prompts/weights only; execution remains governed by
    the existing deterministic risk and execution layers.
    """

    min_improvement: float = 0.03
    agent_scores: dict[str, float] = field(default_factory=dict)
    agent_weights: dict[str, float] = field(default_factory=dict)
    active_prompts: dict[str, str] = field(default_factory=dict)

    def record(self, agent: str, metrics: AgentMetrics) -> dict[str, float]:
        score = score_metrics(metrics)
        self.agent_scores[agent] = score
        self.agent_weights[agent] = bounded_weight(score)
        return {
            "score": score,
            "raw_weight": self.agent_weights[agent],
        }

    def normalized_weights(self) -> dict[str, float]:
        return normalize_weights(self.agent_weights)

    def worst_agent(self) -> str | None:
        if not self.agent_scores:
            return None
        return min(self.agent_scores, key=self.agent_scores.get)

    def evaluate_candidate(
        self,
        *,
        agent: str,
        incumbent_metrics: AgentMetrics,
        candidate_metrics: AgentMetrics,
        candidate_prompt: str,
    ) -> EvolutionDecision:
        incumbent = score_metrics(incumbent_metrics)
        candidate = score_metrics(candidate_metrics)
        improvement = candidate - incumbent

        if improvement >= self.min_improvement:
            self.active_prompts[agent] = candidate_prompt
            self.agent_scores[agent] = candidate
            self.agent_weights[agent] = bounded_weight(candidate)
            return EvolutionDecision(
                agent=agent,
                incumbent_score=incumbent,
                candidate_score=candidate,
                action="PROMOTE",
                reason=f"Candidate improved composite score by {improvement:.4f}.",
                promoted_prompt=candidate_prompt,
            )

        return EvolutionDecision(
            agent=agent,
            incumbent_score=incumbent,
            candidate_score=candidate,
            action="REVERT",
            reason=(
                f"Candidate improvement {improvement:.4f} is below "
                f"required threshold {self.min_improvement:.4f}."
            ),
        )

    def status(self) -> dict:
        return {
            "mode": "shadow_evolution",
            "execution_access": False,
            "min_improvement": self.min_improvement,
            "worst_agent": self.worst_agent(),
            "scores": dict(self.agent_scores),
            "weights": self.normalized_weights(),
            "active_prompt_agents": sorted(self.active_prompts),
        }
