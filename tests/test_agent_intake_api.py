"""Run the real model router in isolation; all records are temporary fixtures."""
import subprocess
import sys
from pathlib import Path


def test_model_router_bridge_credential_intake_and_real_training(tmp_path):
    root=Path(__file__).resolve().parents[1]
    code=r'''
import os, sys, types, tempfile
from pathlib import Path
from datetime import datetime,timedelta,timezone
from fastapi import FastAPI,HTTPException
from fastapi.testclient import TestClient
root=Path.cwd()
sys.path.insert(0,str(root/'runtime/private-api'))
# The owner authenticator itself is unchanged and covered by deployed tests.
# This isolation checks that only the dedicated bridge credential bypasses it.
owner=types.ModuleType('app.runtime_control.routes')
def reject(request): raise HTTPException(status_code=403,detail='owner required')
owner._require_owner=reject
sys.modules['app.runtime_control.routes']=owner
with tempfile.TemporaryDirectory() as directory:
    temp=Path(directory);token='test-only-token-'+('x'*40);(temp/'token.txt').write_text(token)
    os.environ['ATLAS_AGENT_BRIDGE_TOKEN_FILE']=str(temp/'token.txt')
    os.environ['ATLAS_AGENT_OUTCOMES_DB']=str(temp/'outcomes.sqlite3')
    os.environ['ATLAS_AGENT_PERFORMANCE_MODEL']=str(temp/'model')
    from app.performance.agent_routes import router
    app=FastAPI();app.include_router(router);client=TestClient(app);base='/api/runtime/agent-performance'
    headers={'X-Atlas-Model-Bridge':token}
    assert client.get(base+'/status').status_code==403
    assert client.get(base+'/status',headers={'X-Atlas-Model-Bridge':'wrong'}).status_code==401
    status=client.get(base+'/status',headers=headers)
    assert status.status_code==200 and status.json()['dataset']['rows']==0
    for bad in [False,1,'true']:
        assert client.post(base+'/train',headers=headers,json={'confirmed_observed':bad}).status_code==422
    assert client.post(base+'/train',headers=headers,json={'confirmed_observed':True}).status_code==409
    for i in range(60):
        end=datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(seconds=i//2)
        payload=dict(interaction_id='interaction_'+str(i),agent_id='agent_'+str(i%3),agent_experience_months=12+i%30,avg_handle_time_mins=8,historical_csat=2+i%4*.7,total_chats_handled=200+i,current_workload=i%4,sale_success=i%2,csat_outcome=2+i%4*.6,feature_snapshot_at=(end-timedelta(minutes=10)).isoformat(),occurred_at=end.isoformat(),confirmed_observed=True)
        assert client.post(base+'/outcomes',headers=headers,json=payload).status_code==200
    assert client.post(base+'/outcomes',headers=headers,json=payload).json()['dataset']['rows']==60
    trained=client.post(base+'/train',headers=headers,json={'confirmed_observed':True})
    assert trained.status_code==200,trained.text
    data=trained.json()
    assert data['metadata']['source']=='observed' and data['metadata']['rows_test']==12
    assert data['production_ready'] is False and data['broker_execution_allowed'] is False
    assert data['changes_trading_weights'] is False
print('Isolated router: authenticated intake, duplicate handling, grouped chronological training passed.')
'''
    result=subprocess.run([sys.executable,'-c',code],cwd=root,text=True,capture_output=True)
    assert result.returncode==0,result.stdout+result.stderr
