from types import SimpleNamespace
import pytest

@pytest.mark.parametrize("owner,login,expected", [(True,592031391,[349264740]),(False,592031391,[1,349264740]),(True,123,[1,349264740])])
def test_history_cutoff_is_owner_and_account_scoped(monkeypatch, owner, login, expected):
    from app.main import app
    import app.users.routes as routes
    import app.mt5_demo.routes as mt5_routes
    import app.execution_guard.routes as guard_routes
    from app.users.repository import MemoryUserRepository
    monkeypatch.setattr(routes, "require_user", lambda request: SimpleNamespace(user_id="test",email="owner@example.com"))
    monkeypatch.setattr(routes, "_is_owner", lambda user: owner)
    monkeypatch.setattr(routes, "repository", MemoryUserRepository())
    session = {"login":login,"server":"FxPro-MT5 Demo"}
    trades = [{"position_id":1,"time":1790880043},{"position_id":349264740,"time":1790880044}]
    connector = SimpleNamespace(session_credentials=lambda uid: session, get_dashboard_state=lambda uid: {"recent_trades":list(trades)})
    monkeypatch.setattr(mt5_routes, "_service", lambda: connector)
    monkeypatch.setattr(guard_routes, "_service", lambda: SimpleNamespace(status=lambda uid: {}))
    result = routes.user_dashboard(None)["mt5"]
    assert [trade["position_id"] for trade in result["recent_trades"]] == expected
    assert len(trades) == 2
