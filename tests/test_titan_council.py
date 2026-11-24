from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app.intelligence.titan_council import POLICY, TitanEvidence, evaluate_titan
from app.main import app


@pytest.fixture
def evidence():
    return {
        "asset": "BTCUSD", "current_price": 100, "timestamp": "2026-11-20T14:30:00Z",
        "session": "new_york_open", "session_cleared": True,
        "charts": dict.fromkeys(POLICY["timeframes"], True),
        "higher_timeframe_bias": "bullish", "timeframe_conflict": False,
        "regime": "trending", "direction": "long", "sweep_side": "sell_side",
        "high_liquidity": True, "liquidity_analysis": "Sell-side sweep reviewed.",
        "liquidity_target": "Prior swing high.", "smc_analysis": "Confirmed bullish sequence.",
        "checks": dict.fromkeys(POLICY["score_weights"], True),
        "news_risk": "low", "news_cleared": True,
        "account": {"equity": 10000, "daily_loss_pct": 0, "weekly_loss_pct": 0,
                    "monthly_drawdown_pct": 0, "consecutive_losses": 0, "active_positions": 0},
        "levels": {"entry": 100, "stop_loss": 98, "take_profit_1": 107,
                   "take_profit_2": 108, "point_value": 1, "round_trip_cost_per_unit": 0.25},
    }


def assess(data):
    return evaluate_titan(TitanEvidence.model_validate(data))


def test_long_and_short_remain_paper_only(evidence):
    result = assess(evidence)
    assert result["trade_decision"] == "BUY"
    assert result["setup_score"] == 100
    assert result["trade_grade"] == "S"
    assert result["reward_to_risk"] == 3
    assert result["position_risk_pct"] == 0.5
    assert result["risk_budget"] == 50
    assert result["max_units_before_lot_rounding"] == pytest.approx(50 / 2.25)
    assert result["broker_execution_allowed"] is False
    evidence.update(direction="short", higher_timeframe_bias="bearish", sweep_side="buy_side")
    evidence["levels"].update(stop_loss=102, take_profit_1=93, take_profit_2=92)
    assert assess(evidence)["trade_decision"] == "SELL"


@pytest.mark.parametrize("key,value", [
    ("daily_loss_pct", 2), ("weekly_loss_pct", 4), ("monthly_drawdown_pct", 6),
    ("consecutive_losses", 2), ("active_positions", 2),
])
def test_account_limits_stop_at_boundary(evidence, key, value):
    evidence["account"][key] = value
    result = assess(evidence)
    assert result["capital_preservation_verdict"] == "STOP"
    assert result["trade_decision"] == "WAIT"
    assert result["entry"] is None


def test_high_score_cannot_override_a_missing_confirmation(evidence):
    evidence["checks"]["volume_confirmation"] = False
    result = assess(evidence)
    assert result["trade_grade"] == "S"
    assert result["setup_score"] == 95
    assert result["trade_decision"] == "WAIT"


@pytest.mark.parametrize("key,value", [
    ("charts", {"4H": True, "1H": True, "15M": True, "5M": True}),
    ("timeframe_conflict", True), ("timeframe_conflict", None), ("sweep_side", "buy_side"),
    ("news_risk", "high"), ("news_risk", "unknown"), ("regime", "manipulation"),
    ("session_cleared", False), ("timestamp", "2026-11-21T14:30:00Z"),
    ("requested_risk_pct", 1.01), ("account", {}),
])
def test_uncertain_or_disallowed_inputs_wait(evidence, key, value):
    evidence[key] = value
    assert assess(evidence)["trade_decision"] == "WAIT"


def test_costs_can_make_an_apparent_three_r_setup_ineligible(evidence):
    evidence["levels"]["take_profit_1"] = 106
    result = assess(evidence)
    assert result["reward_to_risk"] < 3
    assert result["trade_decision"] == "WAIT"
    assert result["max_units_before_lot_rounding"] is None


def test_invalid_levels_and_overflow_wait(evidence):
    out_of_order = deepcopy(evidence)
    out_of_order["levels"]["take_profit_2"] = 106
    assert assess(out_of_order)["trade_decision"] == "WAIT"
    evidence["levels"]["point_value"] = 1e308
    assert assess(evidence)["trade_decision"] == "WAIT"


def test_endpoints_respect_dashboard_only_public_analysis_gate(monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    monkeypatch.setenv("ATLAS_AGENT_PAPER_EXECUTION_ENABLED", "false")
    monkeypatch.setenv("ATLAS_PUBLIC_ANALYSIS_ENABLED", "false")
    assert client.get("/agent/titan/policy").json() == POLICY
    assert client.post("/agent/titan/analyze", json={}).status_code == 403
    assert client.post("/mt5/test-order").status_code == 403
    monkeypatch.setenv("ATLAS_PUBLIC_ANALYSIS_ENABLED", "true")
    assert client.post("/agent/titan/analyze", json={}).json()["trade_decision"] == "WAIT"


def test_monthly_review_uses_settled_results_and_scores(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    monkeypatch.setenv("ATLAS_PUBLIC_ANALYSIS_ENABLED", "true")
    client = TestClient(app)
    trade = {"settled_at": "2026-11-20T14:30:00Z", "setup": "sweep", "session": "new_york_open",
             "pnl": 120, "initial_risk": 40, "rule_compliant": True, "process_scores": [10] * 6}
    blocked = {**trade, "settled_at": "2026-11-20T14:31:00Z", "setup": "late entry",
               "pnl": -40, "rule_compliant": False, "mistakes": ["Chased price"]}
    response = client.post("/agent/titan/review", json={
        "period": "monthly", "opening_equity": 1000, "trades": [blocked, trade],
    })
    assert response.status_code == 200
    data = response.json()
    assert data["capital_growth"] == 80
    assert data["profit_factor"] == 3
    assert data["average_realized_r"] == 1
    assert data["max_drawdown_pct"] == pytest.approx(40 / 1120 * 100)
    assert data["risk_compliance_pct"] == 50
    assert data["best_setup_by_average_r"] == "sweep"
    assert data["worst_setup_by_average_r"] == "late entry"
    assert data["most_common_mistake"] == "Chased price"
