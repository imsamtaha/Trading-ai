import pytest


def test_council_and_customer_use_separate_terminals(monkeypatch):
    from app.main import app
    from app.mt5_demo.service import MT5DemoService
    monkeypatch.setenv("ATLAS_COUNCIL_MT5_TERMINAL_PATH", r"C:\council\terminal64.exe")
    monkeypatch.setenv("MT5_TERMINAL_PATH", r"C:\customers\terminal64.exe")
    owner = MT5DemoService._default_broker_factory({"login":592031391,"server":"FxPro-MT5 Demo","password":"test"})
    customer = MT5DemoService._default_broker_factory({"login":123,"server":"FxPro-MT5 Demo","password":"test"})
    attached = MT5DemoService._default_broker_factory({"attach_current":True})
    assert owner.config.terminal_path == r"C:\council\terminal64.exe"
    assert attached.config.terminal_path == r"C:\council\terminal64.exe"
    assert customer.config.terminal_path == r"C:\customers\terminal64.exe"


def test_customer_cannot_switch_reserved_council_terminal(monkeypatch):
    from app.main import app
    from app.mt5_demo.service import MT5DemoService, MT5DemoError
    monkeypatch.setenv("ATLAS_COUNCIL_MT5_TERMINAL_PATH", r"C:\council\terminal64.exe")
    monkeypatch.setenv("MT5_TERMINAL_PATH", r"C:\council\terminal64.exe")
    with pytest.raises(MT5DemoError, match="separate MT5 terminal"):
        MT5DemoService._default_broker_factory({"login":123,"server":"FxPro-MT5 Demo","password":"test"})


def test_connect_uses_requested_credentials_before_loading_stale_session(monkeypatch):
    from types import SimpleNamespace
    from app.main import app
    from app.execution import mt5 as module
    account = SimpleNamespace(login=123,server="FxPro-MT5 Demo",trade_mode=0,balance=100,equity=100,currency="USD",trade_allowed=True)
    expected = {"login":123,"password":"test","server":"FxPro-MT5 Demo"}
    fake = SimpleNamespace(initialize=lambda *args, **kwargs: kwargs == expected,
                           login=lambda *args, **kwargs: True, account_info=lambda: account,
                           shutdown=lambda: None, last_error=lambda: (-6,"stale session"))
    monkeypatch.setattr(module, "mt5", fake)
    broker = module.MT5Broker(module.MT5Config(terminal_path=r"C:\customers\terminal64.exe", **expected))
    assert broker.connect()["login"] == 123
