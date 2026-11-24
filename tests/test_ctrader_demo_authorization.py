from contextlib import contextmanager
import os
import stat
from unittest.mock import Mock

import pytest
from dotenv import dotenv_values

from app.integrations.ctrader_demo import DemoConnectionError
from scripts import authorize_ctrader_demo as setup


@pytest.mark.parametrize("callback", [
    "https://untrusted.example/callback?code=abc",
    "https://registered.example/another-path?code=abc",
    "https://registered.example/callback?code=one&code=two",
    "https://registered.example/callback?state=unexpected&code=abc",
    "https://registered.example/callback?error=access_denied",
])
def test_callback_must_match_registered_redirect(callback):
    with pytest.raises(ValueError):
        setup.callback_code("https://registered.example/callback", callback)


def test_callback_accepts_only_matching_redirect_and_code():
    assert setup.callback_code(
        "http://127.0.0.1:8765/callback?mode=demo",
        "http://127.0.0.1:8765/callback?code=enc%2Boded&mode=demo",
    ) == "enc+oded"


def test_exchange_targets_official_endpoint_and_redacts_redirect_error(monkeypatch):
    response = Mock(status_code=302, headers={"Location": "https://untrusted.example/"})
    call = Mock(return_value=response)
    monkeypatch.setattr(setup.requests, "get", call)
    with pytest.raises(DemoConnectionError, match="TOKEN_EXCHANGE_FAILED") as exc:
        setup.exchange_code("client", "private-secret", "https://registered.example/callback", "private-code")
    assert "private" not in str(exc.value)
    assert call.call_args.args == ("https://openapi.ctrader.com/apps/token",)
    assert call.call_args.kwargs["allow_redirects"] is False
    response.json.assert_not_called()


def test_setup_saves_only_after_verified_demo_access(monkeypatch, tmp_path, capsys):
    path = tmp_path / ".env"
    path.write_text("# Retain existing configuration\nKEEP=other-setting\n")
    monkeypatch.setattr(setup, "ENV_PATH", path)
    monkeypatch.setattr(setup.sys.stdin, "isatty", lambda: True)
    monkeypatch.setenv("ATLAS_CTRADER_CLIENT_ID", "approved-app")
    monkeypatch.setenv("ATLAS_CTRADER_CLIENT_SECRET", "private-secret")
    monkeypatch.setenv("ATLAS_CTRADER_DEMO_LOGIN", "12345678")
    monkeypatch.setenv("ATLAS_CTRADER_REDIRECT_URI", "https://registered.example/callback")
    monkeypatch.delenv("ATLAS_CTRADER_MARKET_TOKEN", raising=False)
    monkeypatch.setattr(setup.getpass, "getpass", lambda _: "https://registered.example/callback?code=private-code")
    monkeypatch.setattr(setup, "exchange_code", lambda *args: "private-access-token")

    @contextmanager
    def rejected(credentials):
        raise DemoConnectionError("VIEW_ONLY_AUTHORIZATION_REQUIRED")
        yield

    monkeypatch.setattr(setup, "demo_session", rejected)
    assert setup.main() == 1
    assert "ATLAS_CTRADER" not in path.read_text()
    assert "VIEW_ONLY_AUTHORIZATION_REQUIRED" in capsys.readouterr().err

    @contextmanager
    def accepted(credentials):
        assert credentials.login == "12345678" and credentials.access_token == "private-access-token"
        yield None, 1

    monkeypatch.setattr(setup, "demo_session", accepted)
    assert setup.main() == 0
    saved = dotenv_values(path, interpolate=False)
    assert saved["KEEP"] == "other-setting"
    assert saved["ATLAS_CTRADER_ACCESS_TOKEN"] == "private-access-token"
    assert len(saved["ATLAS_CTRADER_MARKET_TOKEN"]) >= 40
    assert saved["ATLAS_MT5_CONNECTIONS_PAUSED"] == "true"
    assert saved["ATLAS_LIVE_TRADING"] == "false"
    if os.name != "nt":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    output = capsys.readouterr().out
    assert "scope=accounts" in output and "***5678" in output
    assert all(secret not in output for secret in ("private-code", "private-secret", "private-access-token"))
