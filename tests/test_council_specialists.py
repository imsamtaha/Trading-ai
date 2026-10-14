from datetime import datetime,timezone
import importlib.util
import pytest

from app.intelligence.council_adapters import build_paper_council
from app.intelligence.executive import AtlasExecutiveAgent
from app.risk.manager import calculate_risk


def risk_result():
    return calculate_risk('LONG',100,98,104,account_balance=10000,risk_percent=1)


def signal():
    return dict(direction='LONG',confidence=85,reasons=['technical trigger'],strategy='CONTINUATION_5M')


def correlation_context(**changes):
    now=datetime.now(timezone.utc).isoformat()
    return dict(symbol='EURUSD',snapshot_id='s',limit=.8,coefficients={'GBPUSD':.2},
                sample_count=40,bar_seconds=300,available_at=now,last_bar_closed_at=now,
                source='completed_bars',method='pearson_log_returns',**changes)


def test_three_specialist_contracts_keep_risk_out_of_learned_votes():
    assert importlib.util.find_spec('app.intelligence.specialists') is not None,'Council specialists are missing'
    from app.intelligence.specialists import specialist_contracts
    contracts=specialist_contracts()
    assert set(contracts)=={'macro_analyst','quantitative_strategist','risk_executive'}
    assert contracts['macro_analyst']['training_target']=='structural_regime'
    assert contracts['quantitative_strategist']['training_target']=='net_return_r'
    assert contracts['risk_executive']['authority']=='ABSOLUTE_VETO'
    assert contracts['risk_executive']['learned_weight_allowed'] is False


def test_quant_is_one_vote_and_missing_macro_is_explicit():
    result=build_paper_council(symbol='EURUSD',snapshot_id='s',signal=signal(),risk=risk_result(),data_quality=.95,quality={'execution_confidence':70})
    package=result['council'];agents=[row['agent'] for row in package['opinions']]
    assert agents==['quantitative_strategist','macro_analyst']
    assert package['specialists']['macro_analyst']['status']=='DATA_UNAVAILABLE'
    assert package['risk_executive']['authority']=='ABSOLUTE_VETO'
    assert result['trade_intent']['decision']=='BUY'
    assert result['trade_intent']['risk_executive']['allowed'] is True


@pytest.mark.parametrize('value',[False,'true',1,None])
def test_truthy_approval_cannot_defeat_absolute_risk_veto(value):
    risk=dict(risk_result(),approved=value)
    result=build_paper_council(symbol='EURUSD',snapshot_id='s',signal=signal(),risk=risk,data_quality=1)
    assert result['trade_intent']['decision']=='HOLD'
    assert 'RISK_EXECUTIVE_VETO' in result['trade_intent']['reason_codes']


@pytest.mark.parametrize('overrides',[{'position_size':-1},{'position_size':float('nan')},{'actual_risk_amount':200},{'stop_loss':102},{'maximum_risk_amount':None}])
def test_sizing_or_stop_violation_vetoes_high_confidence(overrides):
    risk=dict(risk_result(),**overrides)
    result=build_paper_council(symbol='EURUSD',snapshot_id='s',signal=signal(),risk=risk,data_quality=1)
    assert result['trade_intent']['decision']=='HOLD'


def test_correlation_veto_cannot_be_outvoted_or_disabled_by_training_profile():
    correlation=correlation_context();correlation['coefficients']['GBPUSD']=.95
    result=build_paper_council(symbol='EURUSD',snapshot_id='s',signal=signal(),risk=risk_result(),data_quality=1,open_symbols=['GBPUSD'],correlation=correlation,agent_profile={'agents':{'quantitative_strategist':{'weight':1.5},'risk_executive':{'weight':.5}}})
    assert result['trade_intent']['decision']=='HOLD'
    assert result['council']['risk_executive']['checks']['correlation_limits'] is False
    assert 'CORRELATION_LIMIT_EXCEEDED' in result['council']['risk_executive']['reason_codes']


def test_unknown_correlation_fails_closed_for_existing_exposure():
    result=build_paper_council(symbol='EURUSD',snapshot_id='s',signal=signal(),risk=risk_result(),data_quality=1,open_symbols=['GBPUSD'])
    assert result['trade_intent']['decision']=='HOLD'
    assert 'CORRELATION_DATA_UNAVAILABLE' in result['council']['risk_executive']['reason_codes']


def test_tampering_or_missing_risk_verdict_cannot_enable_new_council_intent():
    package=build_paper_council(symbol='EURUSD',snapshot_id='s',signal=signal(),risk=risk_result(),data_quality=1)['council']
    for verdict in [None,{'allowed':True},{'allowed':True,'authority':'ADVISORY'},{**package['risk_executive'],'snapshot_id':'other'}]:
        altered=dict(package,risk_executive=verdict)
        assert AtlasExecutiveAgent().decide(altered)['decision']=='HOLD'


def test_structural_macro_features_are_not_invented_from_news():
    from app.intelligence.specialists import MacroAnalyst
    state=dict(source='observed',symbol='EURUSD',snapshot_id='s',available_at='2026-01-01T00:00:00Z',regime='INFLATIONARY',market_bias='BEARISH',confidence=.8,features={'policy_rate_change':.25,'inflation_surprise':.2,'order_flow_imbalance':-.3})
    opinion,info=MacroAnalyst().evaluate(state,symbol='EURUSD',snapshot_id='s',as_of='2026-01-01T01:00:00Z')
    assert opinion.agent=='macro_analyst' and opinion.decision=='SELL'
    assert info['regime']=='INFLATIONARY'
    with pytest.raises(ValueError):
        MacroAnalyst().evaluate(dict(state,available_at='2026-01-02T00:00:00Z'),symbol='EURUSD',snapshot_id='s',as_of='2026-01-01T01:00:00Z')


def test_stat_arb_requires_pair_validation_and_costs():
    from app.intelligence.specialists import QuantitativeStrategist
    candidate=dict(signal(),strategy='STAT_ARB_PAIRS')
    opinion,info=QuantitativeStrategist().evaluate(candidate,None,snapshot_id='s')
    assert opinion.decision=='HOLD' and info['status']=='PAIR_VALIDATION_REQUIRED'
    candidate['pair_validation']={'snapshot_id':'s','out_of_sample_validated':True,'costs_included':True}
    assert QuantitativeStrategist().evaluate(candidate,None,snapshot_id='s')[0].decision=='BUY'


def test_paper_monitor_cannot_skip_correlation_veto_when_training_is_off(tmp_path,monkeypatch):
    from app.monitor.atlas_mt5 import AtlasMT5Monitor
    monkeypatch.setenv('ATLAS_LIVE_TRADING','false');monkeypatch.setenv('ATLAS_AUTO_DISCOVER_SYMBOLS','false')
    monkeypatch.setenv('ATLAS_COUNCIL_TRAINING_ENABLED','false')
    monkeypatch.setenv('ATLAS_DEMO_LEDGER',str(tmp_path/'ledger.json'))
    monkeypatch.setenv('ATLAS_SIGNAL_JOURNAL',str(tmp_path/'events.jsonl'))
    monkeypatch.delenv('ATLAS_MAX_ABS_CORRELATION',raising=False)
    monitor=AtlasMT5Monitor(symbols=['EURUSD'])
    existing=monitor.ledger.open_trade(symbol='GBPUSD',direction='LONG',entry=100,stop_loss=98,take_profit=104,position_size=25,risk=risk_result(),strategy='CONTINUATION_5M',confidence=80,timeframe='5m',decision={'decision':'BUY'})
    now=datetime.now(timezone.utc);monkeypatch.setattr(monitor.broker,'quote',lambda symbol:{'ask':100.,'bid':99.99,'time_msc':int(now.timestamp()*1000),'time':int(now.timestamp())})
    result=monitor._open_paper_trade(timestamp=now.isoformat(),symbol='EURUSD',candidate={**signal(),'entry':100,'stop_loss':98,'take_profit':104,'qualified':True,'metadata':{'risk':{'risk_percent':.5}}},decision={'decision':'BUY','confidence':85,'risk_level':'LOW'})
    assert result['status']=='NO_TRADE'
    assert result['risk_executive']['allowed'] is False
    assert monitor.ledger.summary()['open_positions']==1


def test_new_risk_verdict_blocks_the_execution_service_without_broker_call():
    from app.execution.atlas import AtlasExecutionService,ExecutionPolicy
    class Broker:
        config=type('Config',(),{'dry_run':True})()
        def market_order(self,**kwargs): raise AssertionError('Veto must prevent any broker call')
    service=AtlasExecutionService(broker=Broker(),policy=ExecutionPolicy(enabled=True))
    decision={'decision':'BUY','confidence':99,'risk_level':'LOW','specialist_schema_version':1,'snapshot_id':'s','risk_executive':{'allowed':False,'authority':'ABSOLUTE_VETO'}}
    result=service.execute('EURUSD',decision,1,98,104)
    assert result['status']=='BLOCKED' and result['reason']=='RISK_EXECUTIVE_VETO'


def test_correlations_align_closed_bars_and_reject_missing_variance():
    assert importlib.util.find_spec('app.risk.correlation') is not None,'Portfolio correlation reader is missing'
    from app.risk.correlation import measure_correlations
    import math
    now=datetime(2026,1,1,2,tzinfo=timezone.utc)
    end=int(now.timestamp()*1000)
    bars=[{'open_time':end-(60-i)*60000,'close':math.exp(.001*i+.01*math.sin(i))} for i in range(60)]
    other=[dict(bar,close=bar['close']*2) for bar in bars]
    result=measure_correlations('EURUSD',['GBPUSD'],{'EURUSD':bars,'GBPUSD':other},limit=.8,snapshot_id='s',as_of=now.isoformat(),bar_seconds=60)
    assert result['sample_count']>=30 and result['coefficients']['GBPUSD']==pytest.approx(1)
    with pytest.raises(ValueError):
        measure_correlations('EURUSD',['GBPUSD'],{'EURUSD':bars,'GBPUSD':[dict(x,close=1) for x in bars]},limit=.8,snapshot_id='s',as_of=now.isoformat(),bar_seconds=60)


@pytest.mark.parametrize('changes',[
    {'available_at':'1900-01-01T00:00:00Z'}, {'available_at':'2999-01-01T00:00:00Z'},
    {'last_bar_closed_at':'1900-01-01T00:00:00Z'}, {'sample_count':0},
    {'sample_count':True}, {'bar_seconds':0}, {'source':'tick_volume_proxy'},
])
def test_stale_or_unmeasured_correlations_cannot_approve_existing_exposure(changes):
    from app.intelligence.specialists import RiskExecutive
    context=correlation_context();context.update(changes)
    verdict=RiskExecutive().assess(risk_result(),symbol='EURUSD',snapshot_id='s',open_symbols=['GBPUSD'],correlation=context)
    assert verdict['allowed'] is False


def test_fresh_measured_correlation_can_pass():
    from app.intelligence.specialists import RiskExecutive
    assert RiskExecutive().assess(risk_result(),symbol='EURUSD',snapshot_id='s',open_symbols=['GBPUSD'],correlation=correlation_context())['allowed'] is True


@pytest.mark.parametrize('bad_bound',[float('nan'),float('inf'),0,-1,True,None])
def test_malformed_approved_cash_bounds_cannot_reach_broker(bad_bound):
    from app.intelligence.specialists import RiskExecutive
    from app.execution.atlas import AtlasExecutionService,ExecutionPolicy
    class Broker:
        def market_order(self,**kwargs): raise AssertionError('Malformed bounds reached broker')
    verdict=RiskExecutive().assess(risk_result(),symbol='EURUSD',snapshot_id='s')
    verdict['approved_cash_risk']=bad_bound
    decision=dict(decision='BUY',confidence=99,risk_level='LOW',symbol='EURUSD',snapshot_id='s',specialist_schema_version=1,risk_executive=verdict)
    result=AtlasExecutionService(broker=Broker(),policy=ExecutionPolicy(enabled=True)).execute('EURUSD',decision,1,98,104,max_cash_risk=10000)
    assert result['status']=='BLOCKED'


def test_legacy_manual_decision_without_server_risk_verdict_is_blocked():
    from app.execution.atlas import AtlasExecutionService,ExecutionPolicy
    class Broker:
        def market_order(self,**kwargs): raise AssertionError('Legacy bypass reached broker')
    result=AtlasExecutionService(broker=Broker(),policy=ExecutionPolicy(enabled=True)).execute('EURUSD',dict(decision='BUY',confidence=100,risk_level='LOW'),1,98,104)
    assert result['status']=='BLOCKED' and result['reason']=='RISK_EXECUTIVE_VETO'


def test_risk_authority_never_becomes_a_directional_vote_at_either_boundary():
    from app.intelligence.council import AtlasCouncilCoordinator,AgentOpinion
    package=AtlasCouncilCoordinator().build_package(symbol='EURUSD',snapshot_id='s',data_quality=1,
        opinions=[AgentOpinion('quantitative_strategist','BUY',.2),AgentOpinion('risk_executive','SELL',1)],
        senior_risk={'assessment':'RISK_ACCEPTABLE'})
    assert package['conflict_score']==0
    assert AtlasExecutiveAgent().decide(package)['decision']=='BUY'
    package['opinions'].append(dict(agent='risk_executive',decision='SELL',confidence=1,calibrated_confidence=1))
    assert AtlasExecutiveAgent().decide(package)['decision']=='BUY'
