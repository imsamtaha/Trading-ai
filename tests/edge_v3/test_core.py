from dataclasses import replace
from datetime import datetime, timezone, timedelta
import math
import pytest
from atlas_edge.core import EdgeEvidence,evaluate_edge
from atlas_edge.data import Bar,feature_snapshot,triple_barrier
from atlas_edge.events import validate_event


def evidence():
    return EdgeEvidence(.7,.65,2,1,.02,.02,.01,.4,.01,.02,.01,.01,'RISK_ACCEPTABLE',300,'trend-v1','a'*64,True,True)


def test_ev_math_and_caps_preserve_paper_boundary():
    r=evaluate_edge(evidence())
    assert r['decision']=='RESEARCH_CANDIDATE'
    assert r['expected_net_r']==pytest.approx(1.05)
    assert 0<r['risk_fraction']<=.005
    assert r['broker_execution_allowed'] is False and r['live_activation_allowed'] is False


@pytest.mark.parametrize('changes',[
    {'source':'LLM'},{'data_fresh':False},{'model_validated':False},{'risk_approval':'REJECT'},
    {'resolved_oos':199},{'probability':math.nan},{'drawdown':.3},{'ev_lower_r':0},
    {'probability':True},{'data_fresh':'true'},{'probability_lower':.9},{'feature_hash':''},
    {'spread_r':2},{'risk_ceiling':.1},{'ev_lower_r':5},
])
def test_missing_unsafe_or_no_edge_abstains(changes):
    r=evaluate_edge(replace(evidence(),**changes))
    assert r['decision']=='ABSTAIN' and r['risk_fraction']==0


def bars(n=80):
    start=datetime(2026,1,1,tzinfo=timezone.utc)
    return [Bar(start+timedelta(hours=i),start+timedelta(hours=i),100+i,102+i,99+i,101+i,2,1,1) for i in range(n)]


def test_features_are_prefix_invariant_and_delayed_data_is_rejected():
    b=bars();a=feature_snapshot(b,25)
    assert a==feature_snapshot(b[:26],25)
    b[26]=replace(b[26],close=999,high=1000)
    assert a==feature_snapshot(b,25)
    b[25]=replace(b[25],available_at=b[25].time+timedelta(hours=1))
    with pytest.raises(ValueError):feature_snapshot(b,25)


def test_label_next_bar_entry_double_touch_conservative_and_gap_loss():
    b=bars();b[21]=replace(b[21],open=100,high=120,low=80,close=101)
    r=triple_barrier(b,20,1,5,horizon=3)
    assert r['entry_index']==21 and r['gross_r']==-1 and r['net_r']<-1
    b[21]=replace(b[21],high=103,low=99)
    b[22]=replace(b[22],open=80,low=79,high=90,close=85)
    r=triple_barrier(b,20,1,5,horizon=3)
    assert r['reason']=='STOP_GAP' and r['gross_r']==-4


def test_event_schema_never_accepts_direction_or_future_news():
    t=datetime(2026,1,2,tzinfo=timezone.utc)
    e={'event_type':'macro','symbols':['XAUUSD'],'surprise':.3,'novelty':.5,'risk_flag':True,
       'published_at':'2026-01-01T00:00:00Z','available_at':'2026-01-01T00:01:00Z','source':'Bigdata.com cited document'}
    assert validate_event(e,t)['direction_allowed'] is False
    with pytest.raises(ValueError):validate_event({**e,'decision':'BUY'},t)
    with pytest.raises(ValueError):validate_event({**e,'available_at':'2027-01-01T00:00:00Z'},t)


@pytest.mark.parametrize('side,target',[(1,110),(-1,90)])
def test_target_open_gap_precedes_intrabar_stop(side,target):
    b=bars()
    b[21]=replace(b[21],open=100,high=103,low=97,close=100)
    b[22]=replace(b[22],open=target,high=115,low=85,close=100)
    r=triple_barrier(b,20,side,5,horizon=3)
    assert r['reason']=='TARGET_GAP' and r['gross_r']==2
