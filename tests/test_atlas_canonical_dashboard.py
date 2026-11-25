from fastapi.testclient import TestClient

from app.main import app


def test_dashboard_pages_are_retired_and_service_apis_remain():
    with TestClient(app) as client:
        assert client.get("/").json()["api"] == "/api"
        for path in ("/dashboard", "/atlas-ultimate", "/traders", "/centers", "/sam"):
            assert client.get(path).status_code == 410
            assert client.head(path).status_code == 410
        assert client.get("/health").json()["status"] == "healthy"
        assert client.get("/agent/titan/policy").status_code == 200
        assert client.get("/sam/api/snapshot").status_code in (401, 503)
