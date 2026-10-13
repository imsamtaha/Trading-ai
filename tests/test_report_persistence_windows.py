"""Regression: reuse the verified ledger Windows replacement for reports."""
import json
import os
from pathlib import Path
from unittest.mock import patch
import pytest
from app.intelligence.shadow_selector import ShadowSelector
from app.intelligence.recovery_guardian import RecoveryGuardian

@pytest.mark.skipif(os.name!="nt",reason="Windows native replacement")
@pytest.mark.parametrize("kind",["shadow","recovery"])
def test_reports_survive_movefileex_permission_error(tmp_path,kind):
    target=tmp_path/"report.json"
    target.write_text('{"old":true}')
    report={"mode":"SHADOW","generated_at":"2026-10-13T02:15:00+00:00"}
    with patch("os.replace",side_effect=PermissionError("simulated MoveFileEx denial")):
        if kind=="shadow":
            selector=ShadowSelector()
            selector.report=report
            selector.save_report(target)
        else:
            RecoveryGuardian.save_report(report,target)
    assert json.loads(target.read_text())==report
    assert not list(tmp_path.glob("*.tmp"))
