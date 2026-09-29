from datetime import UTC, datetime, timedelta
from app.users.repository import MemoryUserRepository


def test_execution_guard_events_are_user_scoped():
    repo = MemoryUserRepository()
    repo.add_execution_guard_event("alice", {"decision_id": "d1", "status": "BLOCKED"})
    repo.add_execution_guard_event("bob", {"decision_id": "d2", "status": "EXECUTED"})
    assert [e["decision_id"] for e in repo.list_execution_guard_events("alice")] == ["d1"]
    assert [e["decision_id"] for e in repo.list_execution_guard_events("bob")] == ["d2"]


def test_trade_drafts_are_bound_to_user_and_duplicate_ids_are_rejected():
    repo = MemoryUserRepository()
    draft = {"draft_id": "draft-1", "decision_id": "decision-1", "status": "WAITING_CONFIRMATION",
             "expires_at": (datetime.now(UTC) + timedelta(minutes=2)).isoformat()}
    repo.save_trade_draft("alice", draft)
    assert repo.get_trade_draft("alice", "draft-1")["decision_id"] == "decision-1"
    assert repo.get_trade_draft("bob", "draft-1") is None
    try:
        repo.save_trade_draft("alice", draft)
        raised = False
    except ValueError:
        raised = True
    assert raised is True


def test_trade_draft_status_can_be_marked_without_cross_user_access():
    repo = MemoryUserRepository()
    repo.save_trade_draft("alice", {"draft_id": "draft-2", "decision_id": "decision-2",
                                    "status": "WAITING_CONFIRMATION", "expires_at": datetime.now(UTC).isoformat()})
    assert repo.mark_trade_draft("alice", "draft-2", "CONSUMED")["status"] == "CONSUMED"
    assert repo.mark_trade_draft("bob", "draft-2", "CONSUMED") is None
