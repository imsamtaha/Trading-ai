"""ATLAS GIC-style evolution layer.

This package is intentionally isolated from broker execution. It scores agents,
updates bounded influence weights, and manages shadow prompt candidates.
"""

from app.evolution.engine import EvolutionEngine
from app.evolution.models import AgentMetrics, EvolutionDecision

__all__ = ["EvolutionEngine", "AgentMetrics", "EvolutionDecision"]
