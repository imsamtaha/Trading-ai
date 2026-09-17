from datetime import datetime, timezone

from app.risk.ledger_metrics import calculate_ledger_risk_state


class FakeLedger:
    def __init__(self, closed, open_positions):
        self._closed = closed
        self._open = open_positions

    def closed_trades(self):
        return list(self._closed)

    def open_positions(self):
        return list(self._open)


def test_ledger_risk_state_uses_only_current_utc_day_and_actual_open_risk():
    ledger = FakeLedger(
        closed=[
            {
                "closed_at": "2026-09-14T08:00:00+00:00",
                "risk_normalized_pnl": -120.0,
            },
            {
                "closed_at": "2026-09-14T09:00:00+00:00",
                "risk_normalized_pnl": 40.0,
            },
            {
                "closed_at": "2026-09-13T23:59:59+00:00",
                "risk_normalized_pnl": -500.0,
            },
        ],
        open_positions=[
            {"risk_amount": 100.0, "risk_percent": 2.0},
            {"risk_amount": 50.0, "risk_percent": 2.0},
        ],
    )

    result = calculate_ledger_risk_state(
        ledger,
        10000.0,
        now=datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc),
    )

    assert result["daily_realized_pnl"] == -80.0
    assert result["open_risk_amount"] == 150.0
    assert result["open_risk_percent"] == 1.5


def test_ledger_risk_state_supports_legacy_percent_when_risk_amount_missing():
    ledger = FakeLedger(
        closed=[],
        open_positions=[
            {"risk_percent": 0.75},
            {"risk_amount": 25.0, "risk_percent": 1.0},
        ],
    )

    result = calculate_ledger_risk_state(
        ledger,
        10000.0,
        now=datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc),
    )

    assert result["open_risk_percent"] == 1.0
