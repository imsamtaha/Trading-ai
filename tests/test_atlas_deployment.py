from pathlib import Path
import runpy
from unittest.mock import patch
import pytest

@pytest.mark.parametrize("script", ["deploy_atlas_web.py", "deploy_atlas_web_preserving.py"])
@pytest.mark.parametrize("candidate_present", [True, False])
def test_retired_deployer_cannot_replace_current_dashboard(tmp_path, monkeypatch, script, candidate_present):
    production = tmp_path / ".next-production"
    production.mkdir()
    (production/"BUILD_ID").write_text("preserved-build")
    if candidate_present:
        candidate = tmp_path/".next-candidate"
        candidate.mkdir()
        (candidate/"BUILD_ID").write_text("obsolete-candidate")
    before = {str(p.relative_to(tmp_path)):p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    monkeypatch.chdir(tmp_path)
    entrypoint = Path(__file__).parents[1]/"ops"/script
    with patch("subprocess.run", side_effect=AssertionError("Retired publisher must not launch services")):
        with pytest.raises(SystemExit, match="Legacy dashboard deployment is retired.*canonical Sites source"):
            runpy.run_path(str(entrypoint), run_name="__main__")
    after = {str(p.relative_to(tmp_path)):p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert after == before
