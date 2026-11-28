from dataclasses import replace
from datetime import datetime, timezone, timedelta
import json
from atlas_edge.data import Bar
from atlas_edge.research import evaluate_research
from atlas_edge.registry import register_challenger
from atlas_edge.status import status
import pytest


def sample(n=1000):
    t=datetime(2026,1,1,tzinfo=timezone.utc)
    return [Bar(t+timedelta(minutes=i),t+timedelta(minutes=i),100+i*.01,101+i*.01,99+i*.01,100.1+i*.01,2,1,1) for i in range(n)]


def test_research_is_reproducible_holdout_unused_and_missing_old_council_rejects():
    bars=sample();a=evaluate_research(bars,trials=1)
    assert a['status']=='REJECTED' and a['champion_unchanged'] is True
    assert a['holdout']['status']=='NOT_EVALUATED_BY_THIS_RUN'
    assert all('V2_1_BASELINE_UNAVAILABLE' in c['gate_reasons'] for c in a['cost_stress'].values())
    changed=bars[:800]+[replace(b,close=b.close+500,high=b.high+600) for b in bars[800:]]
    b=evaluate_research(changed,trials=1)
    assert a['cost_stress']==b['cost_stress'] and a['resolved_decisions']==b['resolved_decisions']
    assert a['model_id']!=b['model_id'] # Data hashes cover the immutable full input, including holdout.
    assert a['broker_execution_allowed'] is False


def test_registry_is_idempotent_and_never_installs_a_champion(tmp_path):
    report=evaluate_research(sample(),trials=1);path=tmp_path/'registry.json'
    register_challenger(report,path);register_challenger(report,path)
    data=json.loads(path.read_text());assert data['champion'] is None and len(data['challengers'])==1
    assert data['challengers'][report['model_id']]['inference_installed'] is False
    with pytest.raises(ValueError):register_challenger({**report,'model_id':'f'*64},path)


def test_status_projection_is_bounded_and_requires_provenance(tmp_path):
    assert status()['report_state']=='UNAVAILABLE'
    report=evaluate_research(sample(),trials=1);report['generated_at']='2026-01-10T00:00:00+00:00'
    report['account_secret']='must-not-project';path=tmp_path/'report.json';path.write_text(json.dumps(report))
    result=status(path,now=datetime(2026,1,10,1,tzinfo=timezone.utc))
    assert result['report_state']=='LOCAL_RESEARCH_REPORT' and 'account_secret' not in result
    assert result['worker_verified'] is False and result['decision']=='ABSTAIN'
    report['broker_execution_allowed']=True;path.write_text(json.dumps(report))
    assert status(path)['report_state']=='UNAVAILABLE'
