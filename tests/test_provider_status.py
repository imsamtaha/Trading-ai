from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from scripts import atlas_provider_status as service


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ATLAS_PROVIDER_STATUS_TOKEN", "status-test-token")
    return TestClient(service.app)


def test_provider_requires_reader_and_only_exposes_get(client, monkeypatch):
    monkeypatch.setattr(service, "read_demo_account", lambda **_: pytest.fail("Unexpected provider call"))
    assert client.get("/status/ctrader").status_code == 401
    assert client.post("/status/ctrader").status_code == 405


@pytest.mark.parametrize(("active_mode", "expected_status"), [(2, 200), (0, 503)])
def test_mt5_checks_active_account_and_strips_identifiers(client, monkeypatch, active_mode, expected_status):
    for key, value in {
        "ATLAS_LIVE_TRADING": "false", "ATLAS_MT5_STATUS_ACCOUNT_TYPE": "REAL",
        "MT5_TERMINAL_PATH": "real-terminal.exe", "MT5_LOGIN": "7654321", "MT5_SERVER": "Test-Real",
    }.items():
        monkeypatch.setenv(key, value)

    def broker(config):
        assert config.use_active_session and config.dry_run
        return SimpleNamespace(
            connect=lambda: {"login": 7654321, "server": "Test-Real", "trade_mode": active_mode,
                             "balance": 100, "currency": "USD"},
            connected=True,
            disconnect=lambda: None,
        )

    monkeypatch.setattr(service, "MT5Broker", broker)
    result = client.get("/status/mt5", headers={"Authorization": "Bearer status-test-token"})
    assert result.status_code == expected_status
    assert "7654321" not in result.text
    if expected_status == 200:
        assert result.json()["brokerOrders"] is False
        assert result.json()["environment"] == "REAL"


def test_ctrader_reads_optional_demo_without_switching_provider(client, monkeypatch):
    def read_demo_account(*, require_selected):
        assert require_selected is False
        return {"status": "CONNECTED", "environment": "DEMO", "access": "VIEW_ONLY",
                "as_of": "2026-11-27T17:00:00Z", "balance": "200.05", "currency": "USD",
                "broker": "FxPro", "login_masked": "***1234"}

    monkeypatch.setattr(service, "read_demo_account", read_demo_account)
    result = client.get("/status/ctrader", headers={"Authorization": "Bearer status-test-token"})
    assert result.status_code == 200
    assert result.json() == {
        "status": "CONNECTED", "environment": "DEMO", "access": "READ_ONLY",
        "brokerOrders": False, "asOf": "2026-11-27T17:00:00Z", "balance": 200.05,
        "currency": "USD", "broker": "FxPro",
    }
