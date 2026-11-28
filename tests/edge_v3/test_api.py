import json
from pathlib import Path
import subprocess
import sys
from fastapi.testclient import TestClient
from app.main import app


def test_public_research_routes_remain_nonexecuting(monkeypatch):
    monkeypatch.setenv('ATLAS_DASHBOARD_ONLY','true')
    client=TestClient(app)
    p=client.get('/agent/v3/policy');assert p.status_code==200 and p.json()['stage']=='RESEARCH_ONLY'
    s=client.get('/agent/v3/status');assert s.status_code==200 and s.json()['decision']=='ABSTAIN'
    assert client.post('/agent/v3/evaluate',json={'probability':True}).status_code==422
    assert client.post('/mt5/test-order').status_code==403


def test_private_runtime_v3_is_owner_only_and_no_cache():
    root=Path(__file__).resolve().parents[2]
    code='''
from app.main import app
from fastapi.testclient import TestClient
from app.runtime_control import routes
from app.auth.supabase_auth import AuthenticatedUser
from unittest.mock import patch
import os
client=TestClient(app)
assert client.get('/api/runtime/edge-v3').status_code==401
with patch.dict(os.environ,{'ATLAS_OWNER_EMAIL':'owner@example.test'}):
    with patch.object(routes,'require_user',return_value=AuthenticatedUser('other','other@example.test')):
        assert client.get('/api/runtime/edge-v3').status_code==403
    with patch.object(routes,'require_user',return_value=AuthenticatedUser('owner','owner@example.test')):
        r=client.get('/api/runtime/edge-v3')
        assert r.status_code==200 and r.headers['cache-control']=='private, no-store'
        assert r.json()['decision']=='ABSTAIN' and r.json()['worker_verified'] is False
'''
    result=subprocess.run([sys.executable,'-c',code],cwd=root/'runtime/private-api',capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
