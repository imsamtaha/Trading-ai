from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_utc(value: object) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def calculate_ledger_risk_state(
    ledger: Any,
    account_balance: float,
    *,
    now: datetime | None = None,
) -> dict[str, float]:
    """Derive ATLAS portfolio-risk inputs from the persistent paper ledger.

    `daily_realized_pnl` is the sum of today's UTC `risk_normalized_pnl` values
    from closed paper trades. It is intentionally not presented as broker P&L.

    `open_risk_percent` uses persisted `risk_amount` for each open paper trade,
    divided by the current account balance. Legacy entries without a positive
    risk_amount fall back to their stored risk_percent.
    """
    balance = _safe_float(account_balance)
    if balance <= 0:
        raise ValueError("Account balance must be greater than zero.")

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    today = current.astimezone(timezone.utc).date()

    daily_realized_pnl = 0.0
    for trade in ledger.closed_trades():
        closed_at = _parse_utc(trade.get("closed_at"))
        if closed_at is None or closed_at.date() != today:
            continue
        daily_realized_pnl += _safe_float(trade.get("risk_normalized_pnl"))

    open_risk_amount = 0.0
    legacy_open_risk_percent = 0.0
    for position in ledger.open_positions():
        risk_amount = max(0.0, _safe_float(position.get("risk_amount")))
        if risk_amount > 0:
            open_risk_amount += risk_amount
        else:
            legacy_open_risk_percent += max(
                0.0, _safe_float(position.get("risk_percent"))
            )

    open_risk_percent = (open_risk_amount / balance) * 100.0
    open_risk_percent += legacy_open_risk_percent

    return {
        "daily_realized_pnl": round(daily_realized_pnl, 2),
        "open_risk_amount": round(open_risk_amount, 2),
        "open_risk_percent": round(open_risk_percent, 6),
    }
