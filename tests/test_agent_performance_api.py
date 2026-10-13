"""Exercise owner authentication and demo scoring through the actual private router."""
from pathlib import Path
import subprocess
import sys

def test_owner_model_status_and_synthetic_scoring():
    root = Path(__file__).resolve().parents[1]
    code = r'''
import os, tempfile
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.runtime_control import routes as auth_routes
from app.auth.supabase_auth import AuthenticatedUser
from app.performance.agent_xgb import AgentPerformanceXGBoost
client=TestClient(app)
endpoint='/api/runtime/agent-performance'
assert client.get(endpoint+'/status').status_code==401
with tempfile.TemporaryDirectory() as tmp:
    prefix=Path(tmp)/'model'
    with patch.dict(os.environ,{'ATLAS_OWNER_EMAIL':'owner@example.test','ATLAS_AGENT_PERFORMANCE_MODEL':str(prefix)}):
        with patch.object(auth_routes,'require_user',return_value=AuthenticatedUser('other','other@example.test')):
            assert client.get(endpoint+'/status').status_code==403
        with patch.object(auth_routes,'require_user',return_value=AuthenticatedUser('owner','owner@example.test')):
            response=client.get(endpoint+'/status')
            assert response.json()['status']=='UNTRAINED'
            assert response.headers['cache-control']=='private, no-store'
            model=AgentPerformanceXGBoost()
            X,s,c=model.generate_synthetic_data(200)
            model.train(X,s,c,source='synthetic',split='random')
            model.save_models(str(prefix)+'_demo')
            assert client.get(endpoint+'/status').json()['status']=='DEMO_READY'
            agents=X.iloc[:3].astype(float).to_dict('records')
            for index,agent in enumerate(agents):
                agent['agent_id']=str(index)
            payload={'agents':agents}
            assert client.post(endpoint+'/scores',json=payload).status_code==409
            payload['allow_synthetic']=True
            response=client.post(endpoint+'/scores',json=payload)
            assert response.status_code==200,response.text
            result=response.json()
            assert len(result['agents'])==3
            assert result['production_ready'] is False
            assert result['broker_execution_allowed'] is False
            assert result['best_agent_id']==result['agents'][0]['agent_id']
            Path(str(prefix)+'_demo.bundle.zip').write_bytes(b'corrupted')
            assert client.get(endpoint+'/status').json()['status']=='DEGRADED'
            assert client.post(endpoint+'/scores',json=payload).status_code==200
            payload['w_sales']=1
            payload['w_csat']=1
            assert client.post(endpoint+'/scores',json=payload).status_code==422
            payload['w_sales']=.6
            payload['w_csat']=.4
            payload['agents'][1]['agent_id']=payload['agents'][0]['agent_id']
            assert client.post(endpoint+'/scores',json=payload).status_code==422
'''
    result = subprocess.run([sys.executable,"-c",code],
                            cwd=root/"runtime/private-api",capture_output=True,text=True,timeout=60)
    assert result.returncode==0,result.stdout+result.stderr
