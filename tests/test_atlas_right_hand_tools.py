from fastapi.testclient import TestClient

from app.agent.tool_bridge import execute_tool
from app.main import app


def test_write_requires_explicit_approval(monkeypatch):
    monkeypatch.delenv("ATLAS_TOOL_BRIDGE_URL", raising=False)
    result = execute_tool("gmail.write", {"action": "send"}, approved=False)
    assert result["status"] == "APPROVAL_REQUIRED"


def test_unconfigured_bridge_never_claims_execution(monkeypatch):
    monkeypatch.delenv("ATLAS_TOOL_BRIDGE_URL", raising=False)
    result = execute_tool("github.read", {"repo": "imsamtaha/Trading-ai"})
    assert result["status"] == "NOT_CONFIGURED"
    assert "no external action was executed" in result["message"]


def test_unknown_tool_rejected():
    try:
        execute_tool("unknown.tool", {})
    except ValueError as exc:
        assert "Unsupported right-hand tool" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_dashboard_only_allows_tool_status_but_blocks_execution(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    client = TestClient(app)

    status = client.get("/agent/right-hand/tools")
    assert status.status_code == 200
    assert status.json()["write_policy"] == "explicit_approval_required"

    execution = client.post(
        "/agent/right-hand/tools/execute",
        json={"tool": "github.read", "arguments": {}},
    )
    assert execution.status_code == 403
