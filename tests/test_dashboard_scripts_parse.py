import shutil
import subprocess

import pytest


@pytest.mark.skipif(shutil.which('node') is None, reason='Node parser unavailable')
@pytest.mark.parametrize('path', ['/ui/agent-panel.js','/ui/demo-panel.js','/ui/setups-panel.js','/ui/preferences.js'])
def test_served_dashboard_script_is_valid_javascript(monkeypatch, path):
    monkeypatch.setenv('ATLAS_DASHBOARD_ONLY','true')
    from fastapi.testclient import TestClient
    from app.main import app
    response=TestClient(app).get(path)
    assert response.status_code==200
    result=subprocess.run(['node','--check'],input=response.text,text=True,capture_output=True)
    assert result.returncode==0, result.stderr
