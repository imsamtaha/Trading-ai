import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from app.performance.outcomes import OutcomeStore
from app.performance.agent_xgb import AgentPerformanceXGBoost


def outcome(key, offset=0):
    end=datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(seconds=offset)
    return dict(interaction_id=key,agent_id='agent_1',agent_experience_months=12,
        avg_handle_time_mins=8,historical_csat=4,total_chats_handled=200,current_workload=1,
        sale_success=offset%2,csat_outcome=4,confirmed_observed=True,
        feature_snapshot_at=(end-timedelta(minutes=10)).isoformat(),occurred_at=end.isoformat())


def test_simultaneous_distinct_interactions_and_idempotent_retries(tmp_path):
    store=OutcomeStore(tmp_path/'outcomes.sqlite3')
    a=outcome('a');b=outcome('b')
    store.record(a);store.record(b);store.record(a)
    assert store.summary()['rows']==2
    assert [r['interaction_id'] for r in store.rows()]==['a','b']
    with pytest.raises(ValueError,match='INTERACTION_CONFLICT'):
        store.record(dict(a,csat_outcome=2))


def test_legacy_timestamp_constraint_migration_preserves_records(tmp_path):
    path=tmp_path/'outcomes.sqlite3';a=outcome('a')
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE outcomes (interaction_id TEXT PRIMARY KEY, occurred_at TEXT NOT NULL UNIQUE, sale_success INTEGER NOT NULL, recorded_at TEXT NOT NULL, payload TEXT NOT NULL)')
        db.execute('INSERT INTO outcomes VALUES (?,?,?,?,?)',('a',a['occurred_at'],0,'2026-01-02T00:00:00+00:00',json.dumps(a,sort_keys=True)))
    store=OutcomeStore(path);store.record(outcome('b'))
    assert store.summary()['rows']==2
    assert store.rows()[0]==a


def test_chronological_groups_cannot_cross_split_boundaries():
    model=AgentPerformanceXGBoost();X,_,csat=model.generate_synthetic_data(100)
    dates=pd.date_range('2026-01-01',periods=100,freq='s',tz='UTC').tolist()
    dates[58:64]=[dates[58]]*6;dates[78:83]=[dates[78]]*5
    meta=model.train(X,np.arange(100)%2,csat,source='observed',timestamps=dates)
    assert [meta[k] for k in ('rows_train','rows_validation','rows_test')]==[58,20,22]
    periods=meta['time_ranges']
    assert periods['train']['end']<periods['validation']['start']
    assert periods['validation']['end']<periods['test']['start']
    with pytest.raises(ValueError,match='time groups'):
        model.train(X,np.arange(100)%2,csat,source='observed',timestamps=[dates[0]]*100)


def test_os_lock_excludes_other_process_and_releases_after_exit(tmp_path):
    from app.performance.training_lock import training_lock
    prefix=tmp_path/'model'
    code='from app.performance.training_lock import training_lock\nimport sys\nwith training_lock(sys.argv[1]): print("acquired")'
    with training_lock(prefix):
        child=subprocess.run([sys.executable,'-c',code,str(prefix)],capture_output=True,text=True)
        assert child.returncode!=0
        assert 'TRAINING_BUSY' in child.stderr
    child=subprocess.run([sys.executable,'-c',code,str(prefix)],capture_output=True,text=True)
    assert child.returncode==0,child.stderr
    assert child.stdout.strip()=='acquired'


def test_cli_trains_equal_timestamp_groups_and_holds_lock_before_dataset_read(tmp_path):
    from app.performance.training_lock import training_lock
    store=OutcomeStore(tmp_path/'observed.sqlite3')
    for i in range(60):
        row=outcome('row_'+str(i),i//2)
        row['sale_success']=i%2
        row['historical_csat']=2+(i%4)*.7
        row['csat_outcome']=2+(i%4)*.6
        store.record(row)
    prefix=tmp_path/'observed_model'
    command=[sys.executable,'train_agent_performance.py','--observed-store',str(store.path),'--output-prefix',str(prefix)]
    with training_lock(prefix):
        blocked=subprocess.run(command,capture_output=True,text=True)
        assert blocked.returncode!=0 and 'TRAINING_BUSY' in blocked.stderr
        assert not prefix.with_suffix('.bundle.zip').exists()
    result=subprocess.run(command,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    restored=AgentPerformanceXGBoost.load_models(prefix)
    assert restored.metadata['source']=='observed'
    assert restored.metadata['production_ready'] is False
    assert restored.metadata['rows_test']==12
    assert sum(restored.metadata[k] for k in ['rows_train','rows_validation','rows_test'])==60
    X=AgentPerformanceXGBoost.generate_synthetic_data(3)[0]
    assert np.isfinite(restored.predict_composite_score(X)[0]).all()


def test_training_session_provenance_and_baselines_use_only_training_targets():
    model=AgentPerformanceXGBoost();X,_,_=model.generate_synthetic_data(100)
    sales=np.arange(100)%2;csat=np.r_[np.full(60,3.),np.full(20,4.),np.full(20,5.)]
    dates=pd.date_range('2026-01-01',periods=100,freq='s',tz='UTC')
    meta=model.train(X,sales,csat,timestamps=dates)
    assert len(meta['session_id'])==32
    assert len(meta['dataset_sha256'])==64
    assert meta['baselines']['csat_mae']==2
    assert meta['baselines']['sales_logloss']==pytest.approx(-np.log(.5))
    assert meta['best_iterations']['sales']>=0 and meta['best_iterations']['csat']>=0


def test_mixed_iso_timestamp_precision_trains(tmp_path):
    store=OutcomeStore(tmp_path/'mixed.sqlite3')
    for i in range(60):
        row=outcome('mixed_'+str(i),i)
        if i%2:
            stamp=datetime.fromisoformat(row['occurred_at'])+timedelta(microseconds=500000)
            row['occurred_at']=stamp.isoformat()
        store.record(row)
    prefix=tmp_path/'mixed_model'
    result=subprocess.run([sys.executable,'train_agent_performance.py','--observed-store',str(store.path),'--output-prefix',str(prefix)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    restored=AgentPerformanceXGBoost.load_models(prefix)
    assert restored.metadata['rows_test']==12
    dates=[row['occurred_at'] for row in store.rows()]
    X,_,csat=restored.generate_synthetic_data(60)
    restored.train(X,np.arange(60)%2,csat,timestamps=dates)


def test_large_simultaneous_groups_choose_distinct_feasible_boundaries():
    model=AgentPerformanceXGBoost();X,_,csat=model.generate_synthetic_data(100)
    dates=['2026-01-01T00:00:00Z']*60+['2026-01-01T00:00:01Z']*30+['2026-01-01T00:00:02Z']*10
    meta=model.train(X,np.arange(100)%2,csat,timestamps=dates)
    assert [meta[k] for k in ['rows_train','rows_validation','rows_test']]==[60,30,10]
    assert meta['time_ranges']['validation']['end']<meta['time_ranges']['test']['start']
