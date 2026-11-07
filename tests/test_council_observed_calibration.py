from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

import pytest

from app.intelligence.council import AgentOpinion, AtlasCouncilCoordinator
from app.intelligence.council_calibration import (
    calibrated_confidence, chronological_split, observed_examples, train_observed,
)
from app.intelligence.council_training import agent_weight, save_profile


@pytest.fixture
def dataset(tmp_path):
    # Synthetic fixtures test validation only; operational training uses private ledger snapshots.
    journal, trades = [], []
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    for i in range(90):
        opened = start + timedelta(days=i)
        closed = opened + timedelta(minutes=5)
        opinion = {'agent': 'technical', 'decision': 'BUY', 'confidence': .55+(i%4)*.1}
        key = f'fixture-{i}'
        win = i%3 == 0
        journal.append({'timestamp': (closed+timedelta(seconds=1)).isoformat(), 'snapshot_id':key,
                        'realized_direction':'BUY' if win else 'SELL', 'opinions':[opinion],
                        'execution_environment':'PAPER', 'broker_execution_allowed':False})
        quotes = {name:{'bid':1.1,'ask':1.1001,'time':time.timestamp(),'time_msc':time.timestamp()*1000}
                  for name,time in [('entry_quote',opened),('exit_quote',closed)]}
        trades.append({'status':'CLOSED', 'direction':'LONG', 'symbol':'EURUSD', 'r_multiple':1 if win else -1,
                       'opened_at':opened.isoformat(), 'closed_at':closed.isoformat(), **quotes,
                       'quality_card':{'source':'MT5','broker_execution_allowed':False,'quote_offset_seconds':0,'flags':[]},
                       'training_context':{'council':{'snapshot_id':key,'opinions':[opinion]},
                         'trade_intent':{'snapshot_id':key,'execution_environment':'PAPER','broker_execution_allowed':False}}})
    jp, lp = tmp_path/'journal.jsonl', tmp_path/'ledger.json'
    def write():
        jp.write_text(''.join(json.dumps(x)+'\n' for x in journal))
        lp.write_text(json.dumps({'closed_trades':trades,'open_positions':[]}))
    write()
    return jp,lp,journal,trades,write


def test_training_is_chronological_and_read_only(dataset):
    jp,lp,*_ = dataset
    before = jp.read_bytes(),lp.read_bytes()
    profile = train_observed(jp,lp)
    row = profile['agents']['technical']
    assert (row['rows_train'],row['rows_validation'],row['rows_test']) == (54,18,18)
    assert profile['total_examples'] == 90
    assert profile['broker_execution_allowed'] is False
    assert profile['provenance']['broker_fills_verified'] is False
    assert (jp.read_bytes(),lp.read_bytes()) == before
    if row['accepted']:
        assert all(row['metrics'][p]['improvement_vs_stronger_baseline'] >= .005 for p in ('validation','test'))


@pytest.mark.parametrize('mutation', ['duplicate_snapshot','broker','label','prediction','duplicate_agent','timezone','future_label'])
def test_bad_provenance_fails_closed(dataset, mutation):
    jp,lp,journal,trades,write = dataset
    if mutation == 'duplicate_snapshot': journal.append(deepcopy(journal[0]))
    if mutation == 'broker': journal[0]['broker_execution_allowed'] = True
    if mutation == 'label': journal[0]['realized_direction'] = 'SELL'
    if mutation == 'prediction': journal[0]['opinions'] = [{'agent':'technical','decision':'SELL','confidence':.9}]
    if mutation == 'duplicate_agent': journal[0]['opinions'].append(deepcopy(journal[0]['opinions'][0]))
    if mutation == 'timezone': trades[0]['opened_at'] = '2020-01-01T00:00:00'
    if mutation == 'future_label': journal[0]['timestamp'] = '2099-01-01T00:00:00+00:00'
    write()
    with pytest.raises(ValueError): observed_examples(jp,lp)


def test_missing_and_stale_quotes_are_counted_not_invented(dataset):
    jp,lp,journal,trades,write = dataset
    del trades[0]['entry_quote']
    trades[1]['exit_quote']['time_msc'] -= 120000
    write()
    examples,provenance = observed_examples(jp,lp)
    assert len(examples) == 88
    assert provenance['excluded'] == {'missing_mt5_quote_evidence':1, 'stale_or_future_quote':1}


def test_label_overlap_is_purged_without_splitting_time_groups():
    start = datetime(2020,1,1,tzinfo=timezone.utc)
    rows = [{'snapshot_id':str(i),'opened_at':start+timedelta(days=i//2),
             'label_available_at':start+timedelta(days=i//2+2)} for i in range(100)]
    train,val,test,purged = chronological_split(rows)
    assert purged > 0
    assert max(r['label_available_at'] for r in train) < min(r['opened_at'] for r in val)
    assert max(r['label_available_at'] for r in val) < min(r['opened_at'] for r in test)
    assert not {r['opened_at'] for r in train} & {r['opened_at'] for r in val}


def test_holdout_labels_do_not_change_fitted_model(dataset):
    jp,lp,journal,trades,write = dataset
    first = train_observed(jp,lp)['agents']['technical']['model']
    for i in range(72,90):
        trades[i]['r_multiple'] *= -1
        journal[i]['realized_direction'] = 'BUY' if trades[i]['r_multiple'] > 0 else 'SELL'
    write()
    assert train_observed(jp,lp)['agents']['technical']['model'] == first


def test_invalid_profile_and_risk_agents_keep_baseline():
    row = {'accepted':True,'locked_baseline':False,
           'metrics':{p:{'improvement_vs_stronger_baseline':.006} for p in ('validation','test')},
           'model':{'method':'monotonic_platt','intercept':-1,'slope':1}}
    profile = {'version':2,'training_environment':'PAPER','broker_execution_allowed':False,
               'agents':{'technical':row,'risk_executive':{**row,'weight':1.5}}}
    assert calibrated_confidence(profile,'technical',.8) < .8
    assert calibrated_confidence(profile,'risk_executive',.8) == .8
    assert agent_weight(profile,'risk_executive') == 1
    row['metrics']['test']['improvement_vs_stronger_baseline'] = .0049
    assert calibrated_confidence(profile,'technical',.8) == .8


def test_existing_council_rejects_duplicate_agents():
    opinion = AgentOpinion('technical','BUY',.8,(), 's')
    with pytest.raises(ValueError,match='Duplicate'):
        AtlasCouncilCoordinator().build_package(symbol='EURUSD',snapshot_id='s',opinions=[opinion,opinion],senior_risk={},data_quality=1)


def test_profile_save_does_not_corrupt_existing_file_on_invalid_output(tmp_path):
    path = tmp_path/'profile.json'
    save_profile({'version':1},str(path))
    before = path.read_bytes()
    with pytest.raises(ValueError): save_profile({'bad':float('nan')},str(path))
    assert path.read_bytes() == before
    assert not list(tmp_path.glob('*.tmp'))
