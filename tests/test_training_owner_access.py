"""Exercise the real runtime router in an isolated private-api interpreter."""
from pathlib import Path
import subprocess
import sys
import unittest

class TrainingOwnerAccessTests(unittest.TestCase):
    def test_owner_boundary_and_no_cache(self):
        root=Path(__file__).resolve().parents[1]
        code="""
from app.main import app
from fastapi.testclient import TestClient
from app.runtime_control import routes
from app.auth.supabase_auth import AuthenticatedUser
from unittest.mock import patch
import os
client=TestClient(app)
assert client.get('/api/runtime/training').status_code==401
with patch.dict(os.environ,{'ATLAS_OWNER_EMAIL':'owner@example.test'}):
    with patch.object(routes,'require_user',return_value=AuthenticatedUser('other','other@example.test')):
        assert client.get('/api/runtime/training').status_code==403
    with patch.object(routes,'require_user',return_value=AuthenticatedUser('owner','owner@example.test')):
        response=client.get('/api/runtime/training')
        assert response.status_code==200
        assert response.headers['cache-control']=='private, no-store'
        data=response.json()
        assert data['mode']=='PAPER'
        assert 'open_positions' not in data
"""
        result=subprocess.run([sys.executable,"-c",code],cwd=root/"runtime/private-api",capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
if __name__=="__main__":unittest.main()
