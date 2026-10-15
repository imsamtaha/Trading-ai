import importlib.util
from types import SimpleNamespace
import pytest


def engine(equity=100000, **kwargs):
    assert importlib.util.find_spec('app.risk.multi_asset') is not None, 'Multi-asset risk engine is missing'
    from app.risk.multi_asset import MultiAssetRiskEngine
    return MultiAssetRiskEngine(equity, **kwargs)


def health(**kwargs):
    assert importlib.util.find_spec('app.risk.multi_asset') is not None, 'Margin health gate is missing'
    from app.risk.multi_asset import margin_health
    return margin_health(**kwargs)


def test_gold_lots_units_and_margin_are_consistent_and_cost_reserved():
    result=engine().calculate_position('XAUUSD',2650,2635,80000)
    assert result['status']=='APPROVED'
    assert result['lots']==.65 and result['units']==65
    assert result['notional_value']==172250
    assert result['required_margin']==1722.5
    assert result['estimated_spread_cost']==19.5
    assert result['estimated_total_risk']==994.5
    assert result['margin_health']['projected_equity']==99980.5
    assert result['margin_health']['projected_margin_level_pct']==pytest.approx(99980.5/21722.5*100)
    assert result['broker_execution_allowed'] is False


@pytest.mark.parametrize('symbol,entry,stop,step',[
    ('EURUSD',1.1,1.09,.01),('BTCUSD',60000,59000,.01),('SPX500',5000,4950,.1),
])
def test_each_paper_asset_stays_below_budget_and_on_its_lot_step(symbol,entry,stop,step):
    result=engine().calculate_position(symbol,entry,stop,80000)
    assert result['status']=='APPROVED'
    assert result['estimated_total_risk']<=1000
    assert result['lots']/step==pytest.approx(round(result['lots']/step))


def test_broker_minimum_is_rejected_instead_of_rounding_risk_up():
    result=engine(100).calculate_position('XAUUSD',2650,2635,100)
    assert result['status']=='REJECTED_BY_RISK_EXECUTIVE'
    assert 'MINIMUM_LOT_EXCEEDS_RISK' in result['reason_codes']


def test_twenty_percent_and_two_hundred_percent_are_independent_vetoes():
    assert health(equity=1000,used_margin=0,required_margin=200,free_margin=1000)['allowed'] is True
    assert health(equity=1000,used_margin=0,required_margin=200.001,free_margin=1000)['reason_codes']==['MARGIN_USAGE_EXCEEDED']
    result=health(equity=1000,used_margin=400,required_margin=120,free_margin=600)
    assert result['required_margin']<=result['maximum_required_margin']
    assert result['allowed'] is False and 'MARGIN_LEVEL_TOO_LOW' in result['reason_codes']
    assert health(equity=1000,used_margin=450,required_margin=50,free_margin=550)['allowed'] is True


def test_margin_health_uses_the_lower_actual_or_calculated_free_margin():
    result=health(equity=1000,used_margin=600,required_margin=90,free_margin=900)
    assert result['effective_free_margin']==400
    assert result['allowed'] is False


def test_opening_spread_reserve_cannot_drop_projected_level_below_two_hundred():
    result=health(equity=1000,used_margin=450,required_margin=50,free_margin=550,opening_cost=1)
    assert result['allowed'] is False
    assert result['projected_equity']==999 and result['projected_margin_level_pct']==199.8


@pytest.mark.parametrize('position',[{},[],42])
def test_malformed_position_plan_is_a_risk_veto(position):
    from app.intelligence.specialists import RiskExecutive
    from app.risk.manager import calculate_risk
    risk=calculate_risk('LONG',100,98,104)
    assert RiskExecutive().assess(risk,symbol='EURUSD',snapshot_id='s',position=position)['allowed'] is False


@pytest.mark.parametrize('changes',[
    {'entry_price':float('nan')},{'sl_price':0},{'free_margin':float('inf')},
    {'entry_price':True},{'sl_price':2650},{'direction':'SELL'},
])
def test_invalid_position_inputs_fail_closed(changes):
    values=dict(symbol='XAUUSD',entry_price=2650,sl_price=2635,free_margin=80000)
    values.update(changes)
    assert engine().calculate_position(**values)['status']!='APPROVED'


def test_live_symbol_specs_and_account_currency_come_from_broker():
    class Broker:
        def symbol_info(self,symbol): return SimpleNamespace(trade_contract_size=10,volume_min=.1,volume_max=10,volume_step=.1)
        def cash_risk(self,symbol,entry,stop,volume): return abs(entry-stop)*volume*20 # account-currency conversion
        def required_margin(self,symbol,direction,volume,entry): return volume*80
    result=engine(10000,broker=Broker()).calculate_position('XAUUSD.custom',100,90,10000,
        used_margin=0,direction='BUY',entry_includes_spread=True,spread_price=1)
    assert result['status']=='APPROVED' and result['lots']==.5
    assert result['units']==5 and result['required_margin']==40
    assert result['estimated_total_risk']==100 # spread already in actual fill-to-stop distance
    assert result['estimated_spread_cost']==10
    assert result['mode']=='BROKER_ESTIMATE'


def test_broker_stop_inside_spread_cannot_understate_immediate_loss():
    from tests.test_auto_execution import FakeBroker
    result=engine(10000,broker=FakeBroker()).calculate_position('EURUSD',1.1002,1.1001,10000,
        used_margin=0,direction='BUY',entry_includes_spread=True,spread_price=.0002)
    assert result['status']=='REJECTED_BY_RISK_EXECUTIVE'
    assert result['reason_codes']==['STOP_INSIDE_SPREAD']


def test_auto_execution_margin_veto_cannot_be_outvoted():
    from tests.test_auto_execution import FakeBroker,validated_candidate,decision
    from app.execution.auto import AutoExecutionCoordinator,AutoExecutionConfig
    class Broker(FakeBroker):
        def risk_snapshot(self): return dict(super().risk_snapshot(),used_margin=6000,free_margin=4000)
    broker=Broker()
    result=AutoExecutionCoordinator(broker=broker,config=AutoExecutionConfig(enabled=True)).execute_candidate(
        symbol='EURUSD',candidate=validated_candidate(),decision=decision(),account=dict(login=123,server='Test',trade_mode=0))
    assert result['status']=='BLOCKED'
    assert 'MARGIN_LEVEL_TOO_LOW' in result['risk_executive']['reason_codes']
    assert broker.orders==[]
