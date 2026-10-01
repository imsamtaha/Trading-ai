from fastapi.testclient import TestClient

from app.evolution.engine import EvolutionEngine
from app.evolution.models import AgentMetrics
from app.main import app


client = TestClient(app)


def metrics(value: float) -> AgentMetrics:
    return AgentMetrics(
        risk_adjusted_return=value,
        directional_accuracy=value,
        calibration=value,
        drawdown_control=value,
        regime_accuracy=value,
        consistency=value,
    )


def test_evolution_engine_promotes_only_meaningful_improvement():
    engine = EvolutionEngine(min_improvement=0.03)
    decision = engine.evaluate_candidate(
        agent="technical",
        incumbent_metrics=metrics(0.50),
        candidate_metrics=metrics(0.60),
        candidate_prompt="candidate-v2",
    )
    assert decision.action == "PROMOTE"
    assert engine.active_prompts["technical"] == "candidate-v2"


def test_evolution_engine_reverts_weak_candidate():
    engine = EvolutionEngine(min_improvement=0.03)
    decision = engine.evaluate_candidate(
        agent="macro",
        incumbent_metrics=metrics(0.50),
        candidate_metrics=metrics(0.51),
        candidate_prompt="weak-candidate",
    )
    assert decision.action == "REVERT"
    assert "macro" not in engine.active_prompts


def test_evolution_has_no_execution_access():
    engine = EvolutionEngine()
    assert engine.status()["execution_access"] is False
    assert not hasattr(engine, "execute")


def test_evolution_api_is_available():
    response = client.get("/evolution/status")
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "shadow_evolution"
    assert body["execution_access"] is False
