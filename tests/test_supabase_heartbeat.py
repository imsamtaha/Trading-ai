import urllib.error

from app.execution.heartbeat import AtlasHeartbeat


def test_heartbeat_accepts_new_supabase_secret_key(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_test")
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    heartbeat = AtlasHeartbeat(broker=object())

    assert heartbeat.url == "https://example.supabase.co"
    assert heartbeat.key == "sb_secret_test"


def test_new_secret_key_is_sent_as_apikey_not_bearer(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_test")
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b"[]"

    def capture_request(request, timeout=10):
        captured["request"] = request
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", capture_request)
    heartbeat = AtlasHeartbeat(broker=object())

    heartbeat._request("atlas_mt5_connections", "POST", {"status": "connected"})

    request = captured["request"]
    assert request.get_header("Apikey") == "sb_secret_test"
    assert request.get_header("Authorization") is None


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

def test_supabase_timeout_has_no_automatic_post_retry(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_test")
    attempts = []

    def fail_request(request, timeout):
        attempts.append(request.get_method())
        raise TimeoutError("Simulated timeout")

    monkeypatch.setattr("urllib.request.urlopen", fail_request)
    heartbeat = AtlasHeartbeat(broker=object())
    result = heartbeat._request("atlas_execution_events", "POST", {"status": "PAPER"})

    assert result is None
    assert attempts == ["POST"]
    assert "Simulated timeout" in heartbeat.last_error


def test_configurable_supabase_timeout(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_test")
    monkeypatch.setenv("ATLAS_SUPABASE_TIMEOUT", "15")
    captured = []

    def fake_urlopen(request, timeout):
        captured.append(timeout)
        raise TimeoutError("Simulated timeout")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    heartbeat = AtlasHeartbeat(broker=object())
    heartbeat._request("atlas_execution_events", "POST", {"status": "PAPER"})
    assert captured == [15.0]


def test_heartbeat_separates_audit_error_from_mt5_connection(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_test")

    class FakeBroker:
        def connect(self):
            return {"login": 12345, "server": "DEMO"}

    heartbeat = AtlasHeartbeat(broker=FakeBroker())

    def fail_audit(path, method, payload=None):
        heartbeat.last_error = "Simulated audit failure"
        return None

    monkeypatch.setattr(heartbeat, "_request", fail_audit)
    result = heartbeat.heartbeat()
    assert result["mt5_status"] == "connected"
    assert result["audit_status"] == "error"
    assert result["audit_error"] == "Simulated audit failure"


def test_heartbeat_reports_disabled_audit_when_credentials_missing(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    class FakeBroker:
        def connect(self):
            return {"login": 12345, "server": "DEMO"}

    heartbeat = AtlasHeartbeat(broker=FakeBroker())
    result = heartbeat.heartbeat()
    assert result["mt5_status"] == "connected"
    assert result["audit_status"] == "disabled"


def test_heartbeat_detects_empty_patch_result(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_test")

    class FakeBroker:
        def connect(self):
            return {"login": 12345, "server": "DEMO"}

    heartbeat = AtlasHeartbeat(broker=FakeBroker())
    heartbeat.connection_id = "existing-test-id"
    monkeypatch.setattr(heartbeat, "_request", lambda path, method, payload=None: [])
    result = heartbeat.heartbeat()
    assert result["mt5_status"] == "connected"
    assert result["audit_status"] == "error"
    assert "PATCH" in result["audit_error"]


def test_heartbeat_detects_empty_post_result(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_test")

    class FakeBroker:
        def connect(self):
            return {"login": 12345, "server": "DEMO"}

    heartbeat = AtlasHeartbeat(broker=FakeBroker())
    monkeypatch.setattr(heartbeat, "_request", lambda path, method, payload=None: [])
    result = heartbeat.heartbeat()
    assert result["mt5_status"] == "connected"
    assert result["audit_status"] == "error"
    assert result["audit_error"] is not None
