from app.execution.audit import ExecutionAuditLog


def test_audit_records_scope_and_never_accepts_credentials():
    audit = ExecutionAuditLog()
    audit.record(user_id="u1", account_id="100", mode="live_demo", outcome="BLOCKED", reason="EMERGENCY_STOP")
    event = audit.events()[0]
    assert event["user_id"] == "u1"
    assert event["account_id"] == "100"
    assert event["outcome"] == "BLOCKED"
    assert "password" not in event
    assert "token" not in event
