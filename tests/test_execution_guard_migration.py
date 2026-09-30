from pathlib import Path


def test_execution_guard_tables_enable_user_scoped_rls():
    sql = (Path(__file__).parents[1] / "supabase/migrations/20260929_execution_guard_events.sql").read_text(encoding="utf-8-sig").lower()
    assert "alter table public.execution_guard_events enable row level security" in sql
    assert "alter table public.execution_guard_drafts enable row level security" in sql
    assert "auth.uid() = user_id" in sql
    assert "execution_guard_events_user_policy" in sql
    assert "execution_guard_drafts_user_policy" in sql
