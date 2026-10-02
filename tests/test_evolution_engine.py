from fastapi.testclient import TestClient
import pytest

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


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_evolution_rejects_nonfinite_metrics_without_mutating_state(value):
    engine = EvolutionEngine()
    engine.record("technical", metrics(0.9))
    before = engine.status()
    with pytest.raises(ValueError):
        engine.evaluate_candidate(agent="technical", incumbent_metrics=metrics(0.9),
                                  candidate_metrics=metrics(value), candidate_prompt="invalid")
    assert engine.status() == before


def test_evolution_compares_against_stored_incumbent():
    engine = EvolutionEngine()
    engine.record("technical", metrics(0.9))
    result = engine.evaluate_candidate(agent="technical", incumbent_metrics=metrics(0.0),
                                      candidate_metrics=metrics(0.1), candidate_prompt="stale")
    assert result.action == "REVERT"
    assert result.incumbent_score == 0.9
    assert engine.agent_scores["technical"] == 0.9


def test_evolution_accepts_exact_improvement_threshold():
    result = EvolutionEngine().evaluate_candidate(agent="technical", incumbent_metrics=metrics(0.55),
                                                  candidate_metrics=metrics(0.58), candidate_prompt="v2")
    assert result.action == "PROMOTE"


def test_evolution_rejects_stale_version_after_promotion():
    engine = EvolutionEngine()
    engine.record("technical", metrics(0.5))
    version = engine.status()["versions"]["technical"]
    engine.evaluate_candidate(agent="technical", incumbent_metrics=metrics(0.5),
                              candidate_metrics=metrics(0.6), candidate_prompt="v2",
                              expected_version=version)
    with pytest.raises(ValueError, match="version"):
        engine.evaluate_candidate(agent="technical", incumbent_metrics=metrics(0.5),
                                  candidate_metrics=metrics(0.9), candidate_prompt="stale",
                                  expected_version=version)
    assert engine.active_prompts["technical"] == "v2"


def test_evolution_api_returns_conflict_for_stale_version(monkeypatch):
    import app.evolution.api as api
    engine = EvolutionEngine()
    engine.record('technical', metrics(0.5))
    monkeypatch.setattr(api, 'engine', engine)
    monkeypatch.setenv('ATLAS_EVOLUTION_WRITES_ENABLED', 'true')
    monkeypatch.setenv('ATLAS_DASHBOARD_ONLY', 'false')
    payload = {'agent': 'technical', 'incumbent': metrics(0.5).as_dict(),
               'candidate': metrics(0.9).as_dict(), 'candidate_prompt': 'v2', 'expected_version': 1}
    assert client.post('/evolution/evaluate', json=payload).status_code == 200
    assert client.post('/evolution/evaluate', json=payload).status_code == 409
    assert engine.agent_scores['technical'] == 0.9


def test_evolution_concurrent_updates_have_consistent_snapshots():
    from concurrent.futures import ThreadPoolExecutor
    engine = EvolutionEngine()
    def update(index):
        engine.record(str(index), metrics(0.5))
        state = engine.status()
        assert state['scores'].keys() == state['weights'].keys() == state['versions'].keys()
        return state
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(update, range(100)))
    assert len(engine.status()['scores']) == 100
