import json
from datetime import datetime, timezone
from app.runtime_control.server_health import read_server_health

def test_missing_monitor_is_not_reported_healthy(tmp_path):
    assert read_server_health(tmp_path / "absent.json")["state"] == "UNAVAILABLE"

def test_old_heartbeat_is_stale(tmp_path):
    path = tmp_path / "status.json"
    path.write_text(json.dumps({"checked_at_utc": "2026-10-01T00:00:00Z", "components": {}}))
    assert read_server_health(path, now=1790813101)["state"] == "STALE"

def test_fresh_monitor_filters_extra_secret_fields(tmp_path):
    path = tmp_path / "status.json"
    path.write_text(json.dumps({"checked_at_utc": "2026-10-01T00:00:00Z",
        "password": "PRIVATE", "components": {"backend": {"state": "HEALTHY", "secret": "PRIVATE"},
        "mt5": {"state": "HEALTHY", "open_positions": 2}}, "actions": ["STARTED ATLAS Web Frontend"]}))
    result = read_server_health(path, now=1790812860)
    assert result["state"] == "ACTIVE"
    assert result["components"]["backend"] == {"state": "HEALTHY"}
    assert result["components"]["mt5"]["open_positions"] == 2
    assert "PRIVATE" not in json.dumps(result)

def test_corrupt_monitor_is_unavailable(tmp_path):
    path = tmp_path / "status.json"
    path.write_text("broken")
    assert read_server_health(path)["state"] == "UNAVAILABLE"

def test_future_heartbeat_is_not_active(tmp_path):
    path = tmp_path / "status.json"
    path.write_text(json.dumps({"checked_at_utc": "2026-10-01T00:00:00Z", "components": {}}))
    assert read_server_health(path, now=1790810000)["state"] == "STALE"

def test_health_responds_when_sync_worker_pool_is_exhausted():
    import threading
    import anyio
    import httpx
    from app.main import app

    async def scenario():
        limiter = anyio.to_thread.current_default_thread_limiter()
        original_limit = limiter.total_tokens
        limiter.total_tokens = 1
        release = threading.Event()
        occupied = anyio.Event()

        def blocked_provider():
            anyio.from_thread.run_sync(occupied.set)
            release.wait(timeout=5)

        try:
            async with anyio.create_task_group() as tasks:
                tasks.start_soon(anyio.to_thread.run_sync, blocked_provider)
                await occupied.wait()
                try:
                    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                        with anyio.fail_after(1):
                            response = await client.get("/health")
                        assert response.status_code == 200
                        assert response.json()["service"] == "atlas-trading-api"
                finally:
                    release.set()
        finally:
            limiter.total_tokens = original_limit

    anyio.run(scenario)

