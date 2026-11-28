"""ATLAS v3 research-only edge engine; deliberately no execution imports."""
from .core import EdgeEvidence, evaluate_edge, policy

__all__ = ['EdgeEvidence', 'evaluate_edge', 'policy']
