"""ATLAS deterministic scoring and decision-gating components."""

from .engine import (
    AtlasDecision,
    AtlasScoringEngine,
    Bias,
    COMPONENT_WEIGHTS,
    Conviction,
    DecisionStatus,
    Regime,
    RiskFlags,
    ScoringInput,
    calculate_position_size,
)
from .integration import build_scoring_input, score_analysis
from .trade_gate import atlas_decision_to_signal, create_atlas_trade_candidate

__all__ = [
    "AtlasDecision",
    "AtlasScoringEngine",
    "Bias",
    "COMPONENT_WEIGHTS",
    "Conviction",
    "DecisionStatus",
    "Regime",
    "RiskFlags",
    "ScoringInput",
    "calculate_position_size",
    "build_scoring_input",
    "score_analysis",
    "atlas_decision_to_signal",
    "create_atlas_trade_candidate",
]
