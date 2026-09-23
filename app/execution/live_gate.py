"""Owner authorization for the private MT5 order entry point."""

import hmac
import os


class LiveAuthorizationError(ValueError):
    pass


# MetaTrader 5 ACCOUNT_TRADE_MODE enum values.
# Keep these local so importing this authorization module never requires the
# Windows-only MetaTrader5 package.
ACCOUNT_TRADE_MODE_DEMO = 0
ACCOUNT_TRADE_MODE_CONTEST = 1
ACCOUNT_TRADE_MODE_REAL = 2


def authorize_live_order(*, authorization: str | None, confirmed: bool, account: object) -> None:
    """Fail closed unless an owner explicitly approves the pinned real account."""
    token = os.getenv("ATLAS_OWNER_EXECUTION_TOKEN", "")
    login = os.getenv("ATLAS_OWNER_MT5_LOGIN", "")
    if not token or not login or not login.isdecimal():
        raise LiveAuthorizationError("Owner execution credentials are not configured.")
    bearer = authorization.removeprefix("Bearer ") if authorization else ""
    if not authorization or not authorization.startswith("Bearer ") or not hmac.compare_digest(bearer, token):
        raise LiveAuthorizationError("Owner authorization failed.")
    if not confirmed:
        raise LiveAuthorizationError("Explicit order confirmation is required.")
    if account is None or int(getattr(account, "login", -1)) != int(login):
        raise LiveAuthorizationError("Active MT5 account does not match the authorized owner account.")
    if int(getattr(account, "trade_mode", -1)) != ACCOUNT_TRADE_MODE_REAL:
        raise LiveAuthorizationError("The active MT5 account is not a real account.")
    if not bool(getattr(account, "trade_allowed", False)):
        raise LiveAuthorizationError("The active MT5 account does not allow trading.")
