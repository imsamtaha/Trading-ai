import importlib.util
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
import pytest


def dataset(role):
    from app.intelligence.specialists import specialist_contracts
    rng=np.random.default_rng(7);features=specialist_contracts()[role]['features'];n=90
    frame=pd.DataFrame({name:rng.normal(0,.2,n) for name in features})
    if role=='quantitative_strategist': frame['transaction_cost_bps']=rng.uniform(0,2,n)
    base=datetime(2026,1,1,tzinfo=timezone.utc)
    frame['snapshot_at']=[(base+timedelta(hours=i)).isoformat() for i in range(n)]
    frame['available_at']=[(base+timedelta(hours=i,minutes=-1)).isoformat() for i in range(n)]
    frame['label_available_at']=[(base+timedelta(hours=i,minutes=5)).isoformat() for i in range(n)]
    frame['source']='observed'
    target=specialist_contracts()[role]['training_target']
    frame[target]=np.where(np.arange(n)%2,'INFLATIONARY','DISINFLATIONARY') if role=='macro_analyst' else rng.normal(0,1,n)
    return frame


def test_specialist_training_has_two_separate_tasks_and_no_learned_risk_override(tmp_path):
    assert importlib.util.find_spec('app.intelligence.specialist_training') is not None,'Independent training tasks missing'
    from app.intelligence.specialist_training import SpecialistModel
    paths=[]
    for role in ['macro_analyst','quantitative_strategist']:
        model=SpecialistModel(role);meta=model.fit(dataset(role),confirmed_observed=True)
        assert meta['role']==role and meta['production_ready'] is False
        assert meta['rows_test']>0
        paths.append(model.save(tmp_path))
        restored=SpecialistModel.load(tmp_path,role)
        features=meta['features'];X=dataset(role)[features].iloc[:3]
        np.testing.assert_allclose(model.predict(X),restored.predict(X))
    assert paths[0]!=paths[1]
    assert paths[0].exists() and paths[1].exists()
    with pytest.raises(ValueError): SpecialistModel('risk_executive')


def test_training_rejects_unconfirmed_or_future_features_and_unsettled_targets():
    from app.intelligence.specialist_training import SpecialistModel
    model=SpecialistModel('macro_analyst');frame=dataset('macro_analyst')
    with pytest.raises(ValueError): model.fit(frame,confirmed_observed=False)
    with pytest.raises(ValueError): model.fit(frame,confirmed_observed=1)
    with pytest.raises(ValueError): model.fit(frame.assign(available_at='2026-12-01T00:00:00Z'),confirmed_observed=True)
    with pytest.raises(ValueError): model.fit(frame.assign(label_available_at='2027-01-01T00:00:00Z'),confirmed_observed=True)
    with pytest.raises(ValueError): model.fit(frame.assign(source='synthetic'),confirmed_observed=True)


def test_macro_cannot_train_on_paper_profit_labels():
    from app.intelligence.specialist_training import SpecialistModel
    with pytest.raises(ValueError): SpecialistModel('macro_analyst').fit(dataset('macro_analyst').assign(source='paper'),confirmed_observed=True)


def test_specialist_cli_uses_shared_lock_and_requires_observed_confirmation(tmp_path):
    from pathlib import Path
    import subprocess,sys
    from app.performance.training_lock import training_lock
    path=Path('scripts/train_council_specialist.py')
    assert path.exists(),'Specialist training CLI missing'
    csv=tmp_path/'observed.csv';dataset('macro_analyst').to_csv(csv,index=False)
    command=[sys.executable,str(path),'--role','macro_analyst','--csv',str(csv),'--output',str(tmp_path/'models')]
    assert subprocess.run(command,capture_output=True).returncode!=0
    with training_lock(tmp_path/'models'/'macro_analyst'):
        blocked=subprocess.run(command+['--confirmed-observed'],capture_output=True,text=True)
        assert blocked.returncode!=0 and 'TRAINING_BUSY' in blocked.stderr
    result=subprocess.run(command+['--confirmed-observed'],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert (tmp_path/'models'/'macro_analyst.bundle.zip').exists()


def test_specialist_bundle_wrong_role_and_forged_source_are_rejected(tmp_path):
    from app.intelligence.specialist_training import SpecialistModel
    import json,zipfile
    model=SpecialistModel('macro_analyst');model.fit(dataset('macro_analyst'),confirmed_observed=True)
    path=model.save(tmp_path)
    (tmp_path/'quantitative_strategist.bundle.zip').write_bytes(path.read_bytes())
    with pytest.raises(ValueError): SpecialistModel.load(tmp_path,'quantitative_strategist')
    with zipfile.ZipFile(path) as bundle: payload={key:bundle.read(key) for key in bundle.namelist()}
    meta=json.loads(payload['metadata.json']);meta['sources']=['synthetic'];payload['metadata.json']=json.dumps(meta).encode()
    with zipfile.ZipFile(path,'w') as bundle:
        for key,value in payload.items(): bundle.writestr(key,value)
    with pytest.raises(ValueError): SpecialistModel.load(tmp_path,'macro_analyst')
