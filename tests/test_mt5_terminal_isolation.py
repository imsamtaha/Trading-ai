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
