import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
SHELL = shutil.which('powershell')
pytestmark = pytest.mark.skipif(os.name != 'nt' or not SHELL, reason='Windows installer integration')


def run(script, *args):
    return subprocess.run([SHELL, '-NoProfile', '-NonInteractive', '-File', str(script), *map(str,args)],
                          capture_output=True, text=True, timeout=30)


def test_installer_stops_when_native_python_fails(tmp_path):
    fake_python = tmp_path/'failed-python.cmd'
    fake_python.write_text('@exit /b 42\n')
    result = run(ROOT/'ATLAS_COUNCIL_INSTALL.ps1', '-Python', fake_python)
    assert result.returncode != 0
    assert 'policy validation failed' in result.stderr
    assert 'completed successfully' not in result.stdout


def test_installer_stops_when_git_root_cannot_be_verified(tmp_path):
    # A copy below the checkout is still not the repository root.
    copied = tmp_path/'ATLAS_COUNCIL_INSTALL.ps1'
    shutil.copyfile(ROOT/'ATLAS_COUNCIL_INSTALL.ps1',copied)
    result = run(copied)
    assert result.returncode != 0
    assert 'completed successfully' not in result.stdout


def test_installer_rejects_an_unrelated_destination(tmp_path):
    result = run(ROOT/'ATLAS_COUNCIL_INSTALL.ps1','-RepositoryPath',tmp_path)
    assert result.returncode != 0
    assert 'intended checkout' in result.stderr
