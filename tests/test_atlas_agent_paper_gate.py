import pytest

from app.agent.tools import paper_execute


def _trade():
    return {
        "status": "TRADE_CANDIDATE",
        "direction": "LONG",
        "entry": 100.0,
        "stop_loss": 98.0,
        "take_profit": 104.0,
        "risk": {"approved": True, "position_size": 1.0},
    }


def test_paper_execution_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ATLAS_AGENT_PAPER_EXECUTION_ENABLED", raising=False)

    with pytest.raises(PermissionError, match="disabled"):
        paper_execute(1, "XAUUSD", _trade(), confirmed=True)


def test_paper_execution_requires_explicit_confirmation(monkeypatch):
    monkeypatch.setenv("ATLAS_AGENT_PAPER_EXECUTION_ENABLED", "true")

    with pytest.raises(PermissionError, match="confirmation"):
        paper_execute(1, "XAUUSD", _trade(), confirmed=False)


def test_paper_execution_rejects_unapproved_risk(monkeypatch):
    monkeypatch.setenv("ATLAS_AGENT_PAPER_EXECUTION_ENABLED", "true")
    trade = _trade()
    trade["risk"] = {"approved": False, "position_size": 1.0}

    with pytest.raises(ValueError, match="Risk engine"):
        paper_execute(1, "XAUUSD", trade, confirmed=True)
