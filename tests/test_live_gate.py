import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.execution.live_gate import LiveAuthorizationError, authorize_live_order


class LiveGateTests(unittest.TestCase):
    def setUp(self):
        self.account = SimpleNamespace(login=12345, trade_mode=0, trade_allowed=True)

    def check(self, authorization="Bearer secret", confirmed=True, account=None):
        with patch.dict(os.environ, {"ATLAS_OWNER_EXECUTION_TOKEN": "secret", "ATLAS_OWNER_MT5_LOGIN": "12345"}):
            authorize_live_order(authorization=authorization, confirmed=confirmed, account=self.account if account is None else account)

    def test_owner_approved_real_account(self):
        self.check()

    def test_rejects_missing_or_invalid_token(self):
        for header in (None, "Bearer wrong", "secret", "Bearer "):
            with self.subTest(header=header), self.assertRaises(LiveAuthorizationError):
                self.check(authorization=header)

    def test_rejects_unconfirmed_order(self):
        with self.assertRaises(LiveAuthorizationError):
            self.check(confirmed=False)

    def test_rejects_wrong_or_demo_account(self):
        for account in (SimpleNamespace(login=999, trade_mode=0, trade_allowed=True), SimpleNamespace(login=12345, trade_mode=1, trade_allowed=True), SimpleNamespace(login=12345, trade_mode=0, trade_allowed=False)):
            with self.subTest(account=account), self.assertRaises(LiveAuthorizationError):
                self.check(account=account)

    def test_rejects_missing_owner_configuration(self):
        with patch.dict(os.environ, {"ATLAS_OWNER_EXECUTION_TOKEN": "", "ATLAS_OWNER_MT5_LOGIN": ""}):
            with self.assertRaises(LiveAuthorizationError):
                authorize_live_order(authorization="Bearer secret", confirmed=True, account=self.account)


if __name__ == "__main__":
    unittest.main()
