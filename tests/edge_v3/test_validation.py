from datetime import datetime,timedelta,timezone
import math
import pytest
from atlas_edge.validation import calibration,purged_walk_forward,scorecard,block_lower


def test_purge_respects_label_availability_and_embargo():
    start=datetime(2026,1,1,tzinfo=timezone.utc)
    events=[{'decision_index':i,'end_index':i+3,'time':(start+timedelta(hours=i)).isoformat(),
             'label_available_at':(start+timedelta(hours=i+4)).isoformat()} for i in range(80)]
    events[0]['label_available_at']='2027-01-01T00:00:00Z'
    for train,test in purged_walk_forward(events):
        assert 0 not in train
        assert all(events[i]['end_index']<events[test[0]]['decision_index']-1 for i in train)
        assert all(events[i]['label_available_at']<events[test[0]]['time'] for i in train)


def test_calibration_and_nonfinite_rejection():
    assert calibration([0.,1.],[0,1])['brier']==0
    assert calibration([.1,.9],[1,0])['ece']==pytest.approx(.9)
    with pytest.raises(ValueError):calibration([math.nan],[1])
    with pytest.raises(ValueError):block_lower([float('inf')])


def test_baselines_required_no_edge_rejected_and_multiple_trials_declared():
    with pytest.raises(ValueError):scorecard([1]*20,{},probabilities=[1]*20,labels=[1]*20)
    r=scorecard([0]*20,{k:[0]*20 for k in ('cash','trend','random','v2_1')},probabilities=[.5]*20,labels=[0,1]*10)
    assert r['status']=='REJECTED' and 'INSUFFICIENT_OOS_DECISIONS' in r['gate_reasons']
    assert r['broker_execution_allowed'] is False and r['live_activation_allowed'] is False
    assert all(x['status']=='PENDING' for x in r['reviewers'])
