"""The divergent private broker must not become a legacy entry bypass."""
from pathlib import Path
import subprocess
import sys


def test_private_live_entry_boundaries_fail_closed_without_portfolio_risk_context():
    root=Path(__file__).resolve().parents[1]
    code=r'''
import sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'runtime/private-api'))
from app.execution.mt5 import MT5Broker,MT5Config,MT5ExecutionError
from app.execution.atlas import AtlasExecutionService,ExecutionPolicy
from app.mt5_demo.service import MT5DemoService,MT5DemoError
broker=MT5Broker(MT5Config(dry_run=False))
broker.ensure_connected=lambda: (_ for _ in ()).throw(AssertionError('Risk veto must precede MT5 access'))
try:
    broker.market_order('EURUSD','BUY',1,98,104)
    raise AssertionError('Unsupported private live entry accepted')
except MT5ExecutionError as exc:
    assert 'RISK_EXECUTIVE' in str(exc)
class FakeBroker:
    def market_order(self,**kwargs): raise AssertionError('Private execution bypass reached broker')
service=AtlasExecutionService(broker=FakeBroker(),policy=ExecutionPolicy(enabled=True))
assert service.execute('EURUSD',dict(decision='BUY',confidence=100,risk_level='LOW'),1,98,104)['status']=='BLOCKED'
def reject_factory(session): raise AssertionError('Veto must precede broker creation')
manual=MT5DemoService(object(),broker_factory=reject_factory,execution_factory=reject_factory,
                      demo_orders_enabled=True,real_orders_enabled=True,audit_store=object())
manual._sessions['user']=dict(account_type='DEMO',login=123)
state=manual.manual_trading_state('user')
assert state['active'] is False and state['risk_executive_ready'] is False
assert state['blocked_reason']=='RISK_EXECUTIVE_CONTEXT_UNAVAILABLE'
try:
    manual.place_manual_order('user',dict(confirmed=True,account_type='DEMO'))
    raise AssertionError('Manual entry accepted without risk context')
except MT5DemoError as exc:
    assert 'Risk Executive' in str(exc)
assert callable(broker.close_position)
print('Private test-order, manual/demo and broker entries blocked before MT5 access.')
'''
    result=subprocess.run([sys.executable,'-c',code],cwd=root,text=True,capture_output=True)
    assert result.returncode==0,result.stdout+result.stderr
