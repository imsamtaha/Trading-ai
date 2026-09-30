from types import SimpleNamespace
import pytest
from app.execution import mt5 as module
from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError, REAL_MONEY_ACK


class FakeMT5:
    TRADE_ACTION_DEAL = 1
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TIME_GTC = 0
    ORDER_FILLING_IOC = 1
    TRADE_RETCODE_DONE = 10009
    def __init__(self, trade_mode=0):
        self.account = SimpleNamespace(login=1234, trade_mode=trade_mode, trade_allowed=True, equity=10000.0)
        self.sent = []
    def account_info(self):
        return self.account
    def symbol_info_tick(self, symbol):
        return SimpleNamespace(ask=1.2, bid=1.1998)
    def order_calc_profit(self, side, symbol, volume, entry, stop):
        return -1.0
    def order_check(self, request):
        return SimpleNamespace(retcode=0, comment="Done")
    def order_send(self, request):
        self.sent.append(request)
        return SimpleNamespace(retcode=self.TRADE_RETCODE_DONE, order=77, deal=88, volume=request["volume"], price=request["price"], comment="Done")
    def last_error(self):
        return "none"

def broker(monkeypatch, api, config):
    monkeypatch.setattr(module, "mt5", api)
    b = MT5Broker(config)
    b.connected = True
    b.symbol_info = lambda symbol: SimpleNamespace(digits=5, volume_min=0.01, volume_max=100, volume_step=0.01, filling_mode=1)
    return b

def test_demo_order_requires_demo_mode_and_explicit_demo_permission(monkeypatch):
    api = FakeMT5(trade_mode=0)
    b = broker(monkeypatch, api, MT5Config(dry_run=False, demo_order_execution=True))
    result = b.market_order("EURUSD", "BUY", 0.01, 1.19, 1.21, expected_account_type="DEMO", expected_login=1234)
    assert result["status"] == "FILLED"
    assert len(api.sent) == 1
    api.account.trade_mode = 2
    with pytest.raises(MT5ExecutionError, match="account"):
        b.market_order("EURUSD", "BUY", 0.01, 1.19, 1.21, expected_account_type="DEMO", expected_login=1234)
    assert len(api.sent) == 1

def test_real_order_needs_real_policy_and_matching_login(monkeypatch):
    api = FakeMT5(trade_mode=2)
    b = broker(monkeypatch, api, MT5Config(dry_run=False, demo_order_execution=True))
    with pytest.raises(MT5ExecutionError):
        b.market_order("EURUSD", "BUY", 0.01, 1.19, 1.21, expected_account_type="REAL", expected_login=1234)
    assert api.sent == []
    b = broker(monkeypatch, api, MT5Config(dry_run=False, real_money_execution=True, real_money_ack=REAL_MONEY_ACK))
    with pytest.raises(MT5ExecutionError, match="login"):
        b.market_order("EURUSD", "BUY", 0.01, 1.19, 1.21, expected_account_type="REAL", expected_login=9999)
    assert api.sent == []

def test_demo_order_rejects_volume_below_minimum_without_rounding_up(monkeypatch):
    api = FakeMT5()
    b = broker(monkeypatch, api, MT5Config(dry_run=False, demo_order_execution=True))
    with pytest.raises(MT5ExecutionError, match="volume"):
        b.market_order("EURUSD", "BUY", 0.001, 1.19, 1.21, expected_account_type="DEMO", expected_login=1234)
    assert api.sent == []

def test_close_position_cannot_bypass_real_money_policy(monkeypatch):
    api = FakeMT5(trade_mode=2)
    api.POSITION_TYPE_BUY = 0
    api.positions_get = lambda ticket: [SimpleNamespace(ticket=ticket, symbol="EURUSD", type=0, volume=0.01)]
    api.symbol_info = lambda symbol: SimpleNamespace(digits=5, filling_mode=1)
    b = broker(monkeypatch, api, MT5Config(dry_run=False, demo_order_execution=True))
    with pytest.raises(MT5ExecutionError, match="Real-money"):
        b.close_position(55)
    assert api.sent == []

def test_order_rejects_stop_loss_risk_above_one_percent_of_equity(monkeypatch):
    api = FakeMT5(trade_mode=0)
    api.account.equity = 1000.0
    api.order_calc_profit = lambda side, symbol, volume, entry, stop: -25.0
    b = broker(monkeypatch, api, MT5Config(dry_run=False, demo_order_execution=True))
    with pytest.raises(MT5ExecutionError, match="risk"):
        b.market_order("EURUSD", "BUY", 0.01, 1.19, 1.21, expected_account_type="DEMO", expected_login=1234)
    assert api.sent == []
