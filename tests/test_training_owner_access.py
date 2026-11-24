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

    def test_ctrader_mode_blocks_private_mt5_endpoints_and_adapter(self):
        root = Path(__file__).resolve().parents[1]
        code = """
import os
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from app.execution import mt5
from app.main import app

client = TestClient(app)
with patch.dict(os.environ, {'ATLAS_BROKER_PROVIDER': 'ctrader'}):
    native = Mock()
    with patch.object(mt5, 'mt5', native):
        broker = mt5.MT5Broker(mt5.MT5Config())
        try:
            broker.connect()
        except mt5.MT5ExecutionError as exc:
            assert 'paused' in str(exc)
        else:
            raise AssertionError('MT5 connection should be paused')
        native.initialize.assert_not_called()
    assert client.get('/health').json()['mt5_paused'] is True
    assert client.get('/api/mt5-demo/state/').json()['status'] == 'PAUSED'
    assert client.post('/api/mt5-demo/connect').status_code == 503
    assert client.post('/api/runtime/learned-council').status_code == 503
    assert client.get('/api/runtime/training').status_code == 401
"""
        result = subprocess.run(
            [sys.executable, "-c", code], cwd=root / "runtime/private-api",
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__=="__main__":unittest.main()
