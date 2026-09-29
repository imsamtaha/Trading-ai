from datetime import UTC, datetime
import math
import pytest
from pydantic import ValidationError


def base_payload(direction="BUY"):
    return {
        "decision_id": "decision-123",
        "symbol": "EURUSD",
        "direction": direction,
        "confidence": 82.0,
        "rationale": "Council consensus",
        "timestamp": datetime.now(UTC),
        "volume": 0.01,
        "stop_loss": 1.09,
        "take_profit": 1.11,
        "risk_context": {"overall": "LOW"},
    }


def test_actionable_decision_requires_trade_parameters():
    from app.execution_guard.models import CouncilDecision
    for field in ("volume", "stop_loss", "take_profit"):
        payload = base_payload()
        payload[field] = None
        with pytest.raises(ValidationError):
            CouncilDecision(**payload)


def test_wait_may_omit_trade_parameters():
    from app.execution_guard.models import CouncilDecision
    payload = base_payload("WAIT")
    payload.update(volume=None, stop_loss=None, take_profit=None)
    decision = CouncilDecision(**payload)
    assert decision.direction == "WAIT"


def test_non_finite_values_are_rejected():
    from app.execution_guard.models import CouncilDecision
    for field in ("confidence", "volume", "stop_loss", "take_profit"):
        payload = base_payload()
        payload[field] = math.inf
        with pytest.raises(ValidationError):
            CouncilDecision(**payload)
