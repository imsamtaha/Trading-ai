"""Security, provenance, and non-execution checks for the ATLAS /sam owner page."""
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.owner_dashboard import router, read_evidence
from scripts.export_owner_paper_snapshot import collect

isolated = FastAPI()
isolated.include_router(router)
client = TestClient(isolated)
AUTH = ("owner", "example-password-only-for-tests")
KEY = "unit-test-key-with-more-than-32-bytes-123456"


def _configured(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    monkeypatch.setenv("ATLAS_LIVE_TRADING", "false")
    monkeypatch.setenv("ATLAS_OWNER_DASHBOARD_USER", AUTH[0])
    monkeypatch.setenv("ATLAS_OWNER_DASHBOARD_PASSWORD", AUTH[1])
    monkeypatch.setenv("ATLAS_OWNER_SNAPSHOT_HMAC_KEY", KEY)


def _signed_file(path, *, source="PAPER", allow_broker=False, age=0):
    body = {
        "source_environment": source,
        "data_origin": "WINDOWS_PAPER",
        "broker_execution_allowed": allow_broker,
        "as_of": (datetime.now(timezone.utc) - timedelta(hours=age)).isoformat(),
        "source_id": "paper-test-source",
        "data": {
            "council_agents": [{"agent": "technical", "confidence": 0.78, "password": "LEAK"}],
            "paper_trade_history": [{"trade_id": "trade-1", "result_r": 0.8, "secret": "LEAK"}],
            "training_progress": {"before": {"ece": 0.3}, "after": {"ece": 0.12}},
            "mt5_demo": {"status": "RUNNING", "account_type": "DEMO_REPORTED", "password": "LEAK"},
        },
    }
    canonical = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    body["signature"] = hmac.new(KEY.encode(), canonical.encode(), hashlib.sha256).hexdigest()
    path.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    return body


def test_owner_disabled_until_auth_is_configured(monkeypatch):
    monkeypatch.delenv("ATLAS_OWNER_DASHBOARD_USER", raising=False)
    monkeypatch.delenv("ATLAS_OWNER_DASHBOARD_PASSWORD", raising=False)
    assert client.get("/sam").status_code == 503
    assert client.get("/sam/api/snapshot").status_code == 503


def test_owner_requires_auth_for_page_and_snapshot(monkeypatch):
    _configured(monkeypatch)
    assert client.get("/sam").status_code == 401
    assert client.get("/sam/api/snapshot").status_code == 401
    assert client.get("/sam/api/snapshot", auth=("owner", "wrong")).status_code == 401
    assert client.get("/sam", auth=AUTH).status_code == 200
    assert "dir=\"rtl\"" in client.get("/sam", auth=AUTH).text
    assert "LIVE TRADING DISABLED" in client.get("/sam", auth=AUTH).text


def test_owner_refuses_unsafe_execution_configuration(monkeypatch):
    _configured(monkeypatch)
    monkeypatch.setenv("ATLAS_LIVE_TRADING", "true")
    assert client.get("/sam", auth=AUTH).status_code == 503
    monkeypatch.setenv("ATLAS_LIVE_TRADING", "false")
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "false")
    assert client.get("/sam/api/snapshot", auth=AUTH).status_code == 503


def test_unconfigured_snapshot_never_invents_metrics(monkeypatch):
    _configured(monkeypatch)
    monkeypatch.delenv("ATLAS_OWNER_SNAPSHOT_PATH", raising=False)
    resp = client.get("/sam/api/snapshot", auth=AUTH)
    assert resp.status_code == 200
    assert resp.headers["cache-control"] == "no-store"
    data = resp.json()
    assert data["status"] == "UNAVAILABLE"
    assert data["data"]["paper_trade_history"] == []
    assert data["data"]["training_progress"] == {}
    assert data["safeguards"]["real_money_orders_allowed"] is False


def test_rejects_unsigned_and_tampered_snapshot(monkeypatch, tmp_path):
    _configured(monkeypatch)
    path = tmp_path / "snapshot.json"
    body = _signed_file(path)
    monkeypatch.setenv("ATLAS_OWNER_SNAPSHOT_PATH", str(path))
    body.pop("signature")
    path.write_text(json.dumps(body), encoding="utf-8")
    assert read_evidence()["reason"] == "SIGNATURE_MISSING"
    body = _signed_file(path)
    body["source_id"] = "tampered"
    path.write_text(json.dumps(body), encoding="utf-8")
    assert read_evidence()["reason"] == "INVALID_SIGNATURE"


def test_rejects_broker_execution_or_nonpaper_data(monkeypatch, tmp_path):
    _configured(monkeypatch)
    path = tmp_path / "snapshot.json"
    monkeypatch.setenv("ATLAS_OWNER_SNAPSHOT_PATH", str(path))
    _signed_file(path, source="REAL")
    assert read_evidence()["status"] == "UNVERIFIED"
    _signed_file(path, allow_broker=True)
    assert read_evidence()["status"] == "UNVERIFIED"


def test_verified_snapshot_projects_safe_columns_only(monkeypatch, tmp_path):
    _configured(monkeypatch)
    path = tmp_path / "snapshot.json"
    _signed_file(path)
    monkeypatch.setenv("ATLAS_OWNER_SNAPSHOT_PATH", str(path))
    evidence = read_evidence()
    assert evidence["status"] == "VERIFIED"
    assert evidence["data"]["paper_trade_history"][0]["trade_id"] == "trade-1"
    assert "secret" not in evidence["data"]["paper_trade_history"][0]
    assert "password" not in evidence["data"]["mt5_demo"]
    assert evidence["data"]["training_progress"]["after"]["ece"] == 0.12
    assert evidence["safeguards"]["live_trading_enabled"] is False


def test_old_signed_snapshot_is_stale(monkeypatch, tmp_path):
    _configured(monkeypatch)
    path = tmp_path / "snapshot.json"
    _signed_file(path, age=24)
    monkeypatch.setenv("ATLAS_OWNER_SNAPSHOT_PATH", str(path))
    assert read_evidence()["status"] == "STALE"


def test_export_reads_paper_sources_without_modifying_them(tmp_path, monkeypatch):
    monkeypatch.delenv("ATLAS_DEMO_STATUS", raising=False)
    monkeypatch.delenv("ATLAS_DEMO_LEDGER", raising=False)
    monkeypatch.delenv("ATLAS_COUNCIL_PROFILE", raising=False)
    monkeypatch.delenv("ATLAS_COUNCIL_TRAINING_JOURNAL", raising=False)
    monkeypatch.delenv("ATLAS_SIGNAL_JOURNAL", raising=False)
    path = tmp_path / "data"
    path.mkdir()
    status = path / "atlas_demo_status.json"
    status.write_text(json.dumps({"mode": "LIVE_DEMO", "live_execution": False,
        "status": "RUNNING", "cycle_seconds": 30,
        "updated_at": datetime.now(timezone.utc).isoformat()}), encoding="utf-8")
    ledger = path / "atlas_demo_ledger.json"
    ledger.write_text(json.dumps({"open_positions": [], "closed_trades": [
        {"id": "paper-1", "symbol": "EURUSD", "direction": "LONG",
         "opened_at": "2026-11-06T09:00:00+00:00",
         "closed_at": "2026-11-06T09:15:00+00:00",
         "status": "CLOSED", "r_multiple": 0.5, "exit_reason": "TAKE_PROFIT"}
    ]}), encoding="utf-8")
    before = (status.read_bytes(), ledger.read_bytes())
    export = collect(tmp_path)
    assert (status.read_bytes(), ledger.read_bytes()) == before
    assert export["broker_execution_allowed"] is False
    assert export["data"]["paper_trade_history"][0]["result_r"] == 0.5
    assert export["data"]["decision_evidence"] == []
    assert export["data"]["training_progress"]["sample_count"] == 0


def test_export_rejects_nonpaper_worker(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    (d / "atlas_demo_status.json").write_text(
        json.dumps({"mode": "LIVE_EXECUTION", "live_execution": True, "updated_at": "2026-11-07T00:00:00+00:00"}),
        encoding="utf-8")
    (d / "atlas_demo_ledger.json").write_text(json.dumps({"open_positions": [], "closed_trades": []}), encoding="utf-8")
    try:
        collect(tmp_path)
        assert False, "expected refusal"
    except ValueError as exc:
        assert "PAPER" in str(exc)


def test_owner_routes_respect_dashboard_only_guard(monkeypatch):
    from app.main import app
    _configured(monkeypatch)
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    monkeypatch.setenv("ATLAS_LIVE_TRADING", "false")
    with TestClient(app) as app_client:
        assert app_client.get("/sam").status_code == 401
        assert app_client.get("/sam/api/snapshot", auth=AUTH).status_code == 200
        assert app_client.post("/sam/api/snapshot", auth=AUTH).status_code == 403
        assert app_client.post("/mt5/test-order").status_code == 403
