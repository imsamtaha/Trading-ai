import urllib.error

from app.execution.heartbeat import AtlasHeartbeat


def test_heartbeat_accepts_new_supabase_secret_key(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_test")
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    heartbeat = AtlasHeartbeat(broker=object())

    assert heartbeat.url == "https://example.supabase.co"
    assert heartbeat.key == "sb_secret_test"


def test_request_records_http_error_instead_of_silently_discarding(monkeypatch, caplog):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_test")
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    def fail_request(*args, **kwargs):
        raise urllib.error.HTTPError(
            url="https://example.supabase.co/rest/v1/atlas_mt5_connections",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr("urllib.request.urlopen", fail_request)
    heartbeat = AtlasHeartbeat(broker=object())

    result = heartbeat._request("atlas_mt5_connections", "POST", {"status": "connected"})

    assert result is None
    assert heartbeat.last_error is not None
    assert "401" in heartbeat.last_error
    assert "Supabase audit request failed" in caplog.text
