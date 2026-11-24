import importlib.util
from pathlib import Path
from unittest.mock import patch
import pytest

path = Path(__file__).parents[1] / "ops" / "deploy_atlas_web.py"

def module():
    spec=importlib.util.spec_from_file_location("atlas_deploy", path)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def builds(tmp_path):
    web=tmp_path / "web"; web.mkdir()
    for name, value in [(".next-production", "old"), (".next-candidate", "new")]:
        d=web / name; d.mkdir(); (d / "BUILD_ID").write_text(value)
    state=tmp_path / "state"; state.mkdir()
    return web, web / ".next-candidate", state

def test_failed_post_deploy_health_restores_last_good_build(tmp_path):
    w,c,s=builds(tmp_path); d=module(); healthy=iter([False,True])
    with patch.object(d, "task", return_value=None), patch.object(d, "wait_health", side_effect=lambda: next(healthy)):
        with pytest.raises(RuntimeError, match="ROLLED_BACK"):
            d.promote(w,c,s)
    assert (w / ".next-production" / "BUILD_ID").read_text() == "old"
    assert not (s / "maintenance.json").exists()

def test_success_retains_one_last_good_build(tmp_path):
    w,c,s=builds(tmp_path); d=module()
    with patch.object(d, "task", return_value=None), patch.object(d, "wait_health", return_value=True): d.promote(w,c,s)
    assert (w / ".next-production" / "BUILD_ID").read_text() == "new"
    assert (w / ".next-last-good" / "BUILD_ID").read_text() == "old"
    assert not (s / "maintenance.json").exists()

def test_missing_candidate_does_not_touch_production(tmp_path):
    w,c,s=builds(tmp_path); (c / "BUILD_ID").unlink(); d=module()
    with pytest.raises(ValueError): d.promote(w,c,s)
    assert (w / ".next-production" / "BUILD_ID").read_text() == "old"

def test_failed_start_restores_live_directory(tmp_path):
    w,c,s=builds(tmp_path); d=module()
    with patch.object(d, "task", side_effect=[None, RuntimeError("start failed"),None,None]), patch.object(d, "wait_health", return_value=True):
        with pytest.raises(RuntimeError,match="ROLLED_BACK"): d.promote(w,c,s)
    assert (w / ".next-production" / "BUILD_ID").read_text() == "old"
