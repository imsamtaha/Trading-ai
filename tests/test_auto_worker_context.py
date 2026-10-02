import json
import time

import pytest
from scripts import atlas_auto_execution as worker


def context(**changes):
    return {"symbol": "EURUSD", "as_of": time.time(), "source": "runtime-provider",
            "macro_score": 0.0, "news_score": 0.0, "geopolitical_score": 0.0,
            "cross_asset_score": 0.0, "reaction_score": 0.0, "conflict_score": 0.0,
            "volatility_score": 0.0, "event_risk_score": 0.0, **changes}


def candidate():
    return {"symbol": "EURUSD", "direction": "LONG", "regime": "TRENDING_BULL", "confidence": 100.0}


def test_worker_does_not_treat_missing_context_as_zero_risk():
    assert worker._decision(candidate())["decision"] == "NO_TRADE"


@pytest.mark.parametrize("changes", [{"event_risk_score": 0.9}, {"conflict_score": 0.7},
                                     {"volatility_score": 1.0}])
def test_worker_uses_actual_risk_context(changes):
    result = worker._decision(candidate(), context(**changes))
    assert result["decision"] in {"WAIT", "NO_TRADE"}


@pytest.mark.parametrize("changes", [{"as_of": time.time()-1000}, {"symbol": "GBPUSD"},
                                     {"source": ""}, {"news_score": float('nan')},
                                     {"event_risk_score": -0.5}])
def test_worker_rejects_invalid_or_stale_context(changes):
    assert worker._decision(candidate(), context(**changes))["decision"] == "NO_TRADE"


def test_worker_preserves_valid_context_and_scores():
    result = worker._decision(candidate(), context(news_score=0.5, event_risk_score=0.1))
    assert result["event_risk_score"] == 0.1
    assert result["decision"] == "BUY"
    assert result["confidence"] == 65.0


def test_worker_loads_context_from_configured_file(tmp_path, monkeypatch):
    path = tmp_path / "context.json"
    path.write_text(json.dumps(context()))
    monkeypatch.setenv("ATLAS_AUTO_CONTEXT_FILE", str(path))
    assert worker._decision(candidate(), worker.load_runtime_context())["decision"] == "BUY"


def test_worker_loads_root_env_before_startup_gates(tmp_path, monkeypatch, capsys):
    (tmp_path / '.env').write_text('ATLAS_AUTO_EXECUTION_ENABLED=false\nATLAS_LIVE_TRADING=true\n')
    monkeypatch.setattr(worker, 'ROOT', tmp_path)
    monkeypatch.setenv('ATLAS_AUTO_EXECUTION_ENABLED', '')
    monkeypatch.setenv('ATLAS_LIVE_TRADING', '')
    monkeypatch.delenv('ATLAS_AUTO_EXECUTION_ENABLED')
    monkeypatch.delenv('ATLAS_LIVE_TRADING')
    monkeypatch.setattr(worker.sys, 'argv', ['atlas_auto_execution.py'])
    assert worker.main() == 2
    assert worker.os.getenv('ATLAS_LIVE_TRADING') == 'true'
    assert 'BLOCKED' in capsys.readouterr().out


@pytest.mark.parametrize('direction, expected', [('LONG', 'BUY'), ('SHORT', 'SELL')])
def test_worker_preserves_technical_confidence_strength(direction, expected):
    c = {**candidate(), 'direction': direction, 'confidence': 70.0, 'regime': 'TRANSITION'}
    result = worker._decision(c, context())
    assert result['decision'] == 'WAIT'
    assert result['confidence'] == 38.5
    c['confidence'] = 100.0
    result = worker._decision(c, context())
    assert result['decision'] == expected
    assert result['confidence'] == 55.0


@pytest.mark.parametrize('confidence', [None, -1, 101, float('nan'), float('inf')])
def test_worker_rejects_invalid_candidate_evidence(confidence):
    assert worker._decision({**candidate(), 'confidence': confidence}, context())['decision'] == 'NO_TRADE'


def test_worker_rejects_missing_candidate_confidence():
    c = candidate()
    c.pop('confidence')
    assert worker._decision(c, context())['decision'] == 'NO_TRADE'
