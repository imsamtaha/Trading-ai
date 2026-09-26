from types import SimpleNamespace

import app.dashboard.api as dashboard_api
from app.dashboard.preferences import SCRIPT
from app.dashboard.views import DASHBOARD_HTML


class FakeBroker:
    def connect(self):
        return {
            "login": 592031391,
            "server": "FxPro-MT5 Demo",
            "currency": "USD",
            "balance": 10000.0,
            "equity": 9995.0,
            "trade_allowed": True,
            "real_money_execution_enabled": False,
        }

    def symbols(self):
        return []

    def positions(self):
        return []

    def disconnect(self):
        pass


def test_dashboard_api_exposes_account_pending_and_history(monkeypatch):
    fake_mt5 = SimpleNamespace(
        ORDER_TYPE_BUY=0,
        ORDER_TYPE_SELL=1,
        DEAL_TYPE_BUY=0,
        DEAL_TYPE_SELL=1,
        DEAL_ENTRY_IN=0,
        DEAL_ENTRY_OUT=1,
        account_info=lambda: SimpleNamespace(
            login=592031391,
            server="FxPro-MT5 Demo",
            trade_mode=0,
            company="FxPro Markets Ltd.",
            margin=0.0,
            margin_free=9995.0,
            profit=-5.0,
            leverage=100,
        ),
        orders_get=lambda: [SimpleNamespace(
            ticket=22, symbol="EURUSD", type=0, volume_initial=0.10,
            price_open=1.1000, sl=1.0900, tp=1.1200, time_setup=1700000000,
        )],
        history_deals_get=lambda start, end: [SimpleNamespace(
            ticket=33, position_id=44, symbol="GOLD", type=1, entry=1,
            volume=0.05, price=2600.0, profit=12.5, time=1700000100,
        )],
    )
    monkeypatch.setattr(dashboard_api, "MT5Broker", lambda config: FakeBroker())
    monkeypatch.setattr(dashboard_api.MT5Config, "from_env", classmethod(lambda cls: object()))
    monkeypatch.setattr(dashboard_api, "mt5", fake_mt5)
    monkeypatch.setattr(dashboard_api, "build_universe", lambda symbols, top_n: [])
    monkeypatch.setattr(
        dashboard_api,
        "_market_intelligence",
        SimpleNamespace(snapshot=lambda: {"status": "ONLINE"}),
    )
    state = dashboard_api.atlas_dashboard_state()

    assert state["account"]["badge"] == "DEMO · FxPro-MT5 Demo · ***1391"
    assert len(state["pending_orders"]) == 1
    assert state["pending_orders"][0]["symbol"] == "EURUSD"
    assert state["pending_orders"][0]["direction"] == "BUY"
    assert len(state["recent_trades"]) == 1
    assert state["recent_trades"][0]["symbol"] == "GOLD"
    assert state["recent_trades"][0]["direction"] == "SELL"
    assert state["recent_trades"][0]["profit"] == 12.5


def test_dashboard_contains_mt5_activity_tabs_and_arabic_labels():
    for token in (
        'id="mt5Activity"',
        'data-activity-tab="open"',
        'data-activity-tab="pending"',
        'data-activity-tab="history"',
        'id="activityOpen"',
        'id="activityPending"',
        'id="activityHistory"',
        'id="accountBadge"',
    ):
        assert token in DASHBOARD_HTML

    for pair in (
        "'MT5 Activity':'نشاط MT5'",
        "'Open':'مفتوحة'",
        "'Pending':'معلّقة'",
        "'History':'السجل'",
    ):
        assert pair in SCRIPT
