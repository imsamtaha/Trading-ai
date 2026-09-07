from app.agent.core import AtlasAgent
from app.agent.models import AgentRequest


def test_agent_returns_wait_when_no_trade(monkeypatch):
    monkeypatch.setattr(
        "app.agent.core.market_analysis",
        lambda **kwargs: {
            "symbol": "XAUUSD",
            "interval": "1h",
            "technical": {"trend": "neutral", "momentum": "bearish"},
            "structure": {"bias": "neutral"},
            "signal": {"direction": "WAIT", "confidence": 42},
            "trade": {"status": "NO_TRADE", "reason": "Signal is not actionable."},
        },
    )

    result = AtlasAgent().assess(AgentRequest(symbol="XAUUSD"))

    assert result.decision == "WAIT"
    assert result.paper_only is True
    assert result.status == "NO_TRADE"
    assert "risk-management" not in result.selected_skills


def test_agent_marks_only_risk_approved_setup_as_paper_candidate(monkeypatch):
    trade = {
        "status": "TRADE_CANDIDATE",
        "direction": "LONG",
        "entry": 100.0,
        "stop_loss": 98.0,
        "take_profit": 104.0,
        "risk": {"approved": True, "position_size": 1.0},
    }
    monkeypatch.setattr(
        "app.agent.core.market_analysis",
        lambda **kwargs: {
            "symbol": "EURUSD",
            "interval": "1h",
            "technical": {"trend": "bullish", "momentum": "bullish"},
            "structure": {"bias": "bullish"},
            "signal": {"direction": "LONG", "confidence": 76},
            "trade": trade,
        },
    )
    monkeypatch.setattr(
        "app.agent.core.risk_evaluate",
        lambda *args, **kwargs: {"approved": True, "risk_reward": 2.0},
    )

    result = AtlasAgent().assess(AgentRequest(symbol="EURUSD"))

    assert result.decision == "PAPER_CANDIDATE"
    assert result.risk["approved"] is True
    assert "risk-management" in result.selected_skills
