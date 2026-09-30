from fastapi.testclient import TestClient

from app.mt5_demo.service import MT5DemoError, MT5DemoService
from app.users.repository import MemoryUserRepository


class FakeBroker:
    def __init__(self, account):
        self.account = account
        self.disconnected = False

    def connect(self):
        return dict(self.account)

    def disconnect(self):
        self.disconnected = True


def test_attach_current_demo_stores_no_password():
    repo = MemoryUserRepository()
    broker = FakeBroker({"login": 1234561391, "server": "FxPro-MT5 Demo", "account_type": "DEMO"})
    service = MT5DemoService(repo, broker_factory=lambda credentials: broker)

    result = service.attach_current_demo("owner-1")

    assert result["connected"] is True
    assert result["account_masked"] == "***1391"
    session = service.session_credentials("owner-1")
    assert session is not None
    assert "password" not in session
    assert session["attach_current"] is True
