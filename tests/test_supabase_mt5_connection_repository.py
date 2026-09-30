from __future__ import annotations


def test_clear_mt5_connection_deletes_from_private_demo_table(monkeypatch):
    from app.users.repository import SupabaseUserRepository

    captured = {}
    class Response:
        ok = True

    def fake_delete(url, **kwargs):
        captured["url"] = url
        return Response()

    repo = SupabaseUserRepository.__new__(SupabaseUserRepository)
    repo.base_url = "https://example.supabase.co"
    repo.publishable_key = "test"
    repo._headers = lambda prefer="return=representation": {}
    monkeypatch.setattr("app.users.repository.requests.delete", fake_delete)
    repo.clear_mt5_connection("user-a")
    assert captured["url"].endswith("/rest/v1/atlas_user_mt5_demo_connections")