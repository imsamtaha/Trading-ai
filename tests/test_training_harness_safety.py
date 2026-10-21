import json

import numpy as np
import pytest
pytest.importorskip('pandas')
pytest.importorskip('sklearn')

from atlas_training.train_agent import calibration_error, evaluate_promotion_gate, write_council_report, champion_score


@pytest.mark.parametrize('key', ['oos_mean', 'stability', 'calibration_error'])
@pytest.mark.parametrize('value', [float('nan'), float('inf'), -1])
def test_invalid_metrics_cannot_promote(key, value):
    metrics = dict(oos_mean=.6, stability=.9, calibration_error=.05)
    metrics[key] = value
    assert not evaluate_promotion_gate(metrics, None)[0]


def test_bin_errors_cannot_cancel():
    # Mean confidence and accuracy match, but the two bins are miscalibrated.
    assert calibration_error(np.array([.6] * 5 + [.8] * 5), [1]*5 + [1, 1, 0, 0, 0]) == pytest.approx(.4)


def test_imbalanced_baseline_blocks_misleading_accuracy():
    metrics = dict(oos_mean=.7, stability=.9, calibration_error=.05, baseline_oos=.8)
    assert not evaluate_promotion_gate(metrics, None)[0]


def test_report_is_evidence_not_council_permission(tmp_path):
    target = tmp_path / 'report.json'
    write_council_report(target, agent='trend', metrics={'oos_mean': .6}, eligible=True,
                         reasons=[], run_id='run-1', version=1)
    result = json.loads(target.read_text())
    assert result['status'] == 'SHADOW_REVIEW'
    assert result['reviewers'] == ['STC-04', 'STC-09']
    assert result['broker_execution_allowed'] is False
    assert result['council_weight_activation'] is False


def test_report_failure_preserves_previous_document(tmp_path):
    target = tmp_path / 'report.json'
    target.write_text('{"previous":true}')
    with pytest.raises(ValueError):
        write_council_report(target, agent='trend', metrics={'oos_mean': float('nan')},
                             eligible=True, reasons=[], run_id='run-1', version=1)
    assert json.loads(target.read_text()) == {'previous': True}


def test_existing_registry_without_champion_is_uninitialized():
    pytest.importorskip('mlflow')
    from types import SimpleNamespace
    client = SimpleNamespace(get_registered_model=lambda name: SimpleNamespace(aliases={'challenger': '1'}))
    assert champion_score(client, 'atlas-trend') is None


def test_registry_backend_failure_is_not_a_missing_champion():
    pytest.importorskip('mlflow')
    from types import SimpleNamespace
    from mlflow.exceptions import MlflowException
    def fail(name):
        raise MlflowException('backend unavailable', error_code='INTERNAL_ERROR')
    with pytest.raises(MlflowException, match='backend unavailable'):
        champion_score(SimpleNamespace(get_registered_model=fail), 'atlas-trend')
