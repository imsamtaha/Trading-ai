from app.risk.engine import RiskScoreEngine


def test_low_risk_candidate_is_eligible():
    engine = RiskScoreEngine()

    result = engine.evaluate(
        risk_percent=0.50,
        daily_loss_percent=0.0,
        weekly_loss_percent=0.0,
        drawdown_percent=0.0,
        open_positions=0,
        same_symbol_positions=0,
        spread_ok=True,
        data_fresh=True,
        stop_loss_valid=True,
    )

    assert result["risk_score"] <= 30
    assert result["risk_level"] == "ELIGIBLE"
    assert result["action"] == "ALLOW_DEMO"

def test_invalid_stop_loss_returns_audit_reason():
    engine = RiskScoreEngine()

    result = engine.evaluate(
        risk_percent=0.50,
        daily_loss_percent=0.0,
        weekly_loss_percent=0.0,
        drawdown_percent=0.0,
        open_positions=0,
        same_symbol_positions=0,
        spread_ok=True,
        data_fresh=True,
        stop_loss_valid=False,
    )

    assert result["action"] == "BLOCK"
    assert result["risk_level"] == "HARD_BLOCK"
    assert result["reasons"] == ["INVALID_STOP_LOSS"]

def test_invalid_stop_loss_returns_audit_reason():
    engine = RiskScoreEngine()

    result = engine.evaluate(
        risk_percent=0.50,
        daily_loss_percent=0.0,
        weekly_loss_percent=0.0,
        drawdown_percent=0.0,
        open_positions=0,
        same_symbol_positions=0,
        spread_ok=True,
        data_fresh=True,
        stop_loss_valid=False,
    )

    assert result["action"] == "BLOCK"
    assert result["risk_level"] == "HARD_BLOCK"
    assert result["reasons"] == ["INVALID_STOP_LOSS"]

def test_stale_data_is_hard_blocked_with_reason():
    engine = RiskScoreEngine()

    result = engine.evaluate(
        risk_percent=0.50,
        daily_loss_percent=0.0,
        weekly_loss_percent=0.0,
        drawdown_percent=0.0,
        open_positions=0,
        same_symbol_positions=0,
        spread_ok=True,
        data_fresh=False,
        stop_loss_valid=True,
    )

    assert result["action"] == "BLOCK"
    assert result["risk_level"] == "HARD_BLOCK"
    assert result["reasons"] == ["STALE_DATA"]

def test_excessive_spread_is_hard_blocked_with_reason():
    engine = RiskScoreEngine()

    result = engine.evaluate(
        risk_percent=0.50,
        daily_loss_percent=0.0,
        weekly_loss_percent=0.0,
        drawdown_percent=0.0,
        open_positions=0,
        same_symbol_positions=0,
        spread_ok=False,
        data_fresh=True,
        stop_loss_valid=True,
    )

    assert result["action"] == "BLOCK"
    assert result["risk_level"] == "HARD_BLOCK"
    assert result["reasons"] == ["EXCESSIVE_SPREAD"]

def test_daily_loss_limit_blocks_execution():
    engine = RiskScoreEngine()

    result = engine.evaluate(
        risk_percent=0.50,
        daily_loss_percent=2.0,
        weekly_loss_percent=0.0,
        drawdown_percent=0.0,
        open_positions=0,
        same_symbol_positions=0,
        spread_ok=True,
        data_fresh=True,
        stop_loss_valid=True,
    )

    assert result["action"] == "BLOCK"
    assert result["reasons"] == ["DAILY_LOSS_LIMIT"]

def test_weekly_loss_limit_blocks_execution():
    engine = RiskScoreEngine()

    result = engine.evaluate(
        risk_percent=0.50,
        daily_loss_percent=0.0,
        weekly_loss_percent=4.0,
        drawdown_percent=0.0,
        open_positions=0,
        same_symbol_positions=0,
        spread_ok=True,
        data_fresh=True,
        stop_loss_valid=True,
    )

    assert result["action"] == "BLOCK"
    assert result["reasons"] == ["WEEKLY_LOSS_LIMIT"]

def test_max_drawdown_blocks_execution():
    engine = RiskScoreEngine()

    result = engine.evaluate(
        risk_percent=0.50,
        daily_loss_percent=0.0,
        weekly_loss_percent=0.0,
        drawdown_percent=6.0,
        open_positions=0,
        same_symbol_positions=0,
        spread_ok=True,
        data_fresh=True,
        stop_loss_valid=True,
    )

    assert result["action"] == "BLOCK"
    assert result["reasons"] == ["MAX_DRAWDOWN"]

def test_max_open_positions_blocks_execution():
    engine = RiskScoreEngine()

    result = engine.evaluate(
        risk_percent=0.50,
        daily_loss_percent=0.0,
        weekly_loss_percent=0.0,
        drawdown_percent=0.0,
        open_positions=3,
        same_symbol_positions=0,
        spread_ok=True,
        data_fresh=True,
        stop_loss_valid=True,
    )

    assert result["action"] == "BLOCK"
    assert result["reasons"] == ["MAX_OPEN_POSITIONS"]

def test_same_symbol_position_limit_blocks_execution():
    engine = RiskScoreEngine()

    result = engine.evaluate(
        risk_percent=0.50,
        daily_loss_percent=0.0,
        weekly_loss_percent=0.0,
        drawdown_percent=0.0,
        open_positions=1,
        same_symbol_positions=1,
        spread_ok=True,
        data_fresh=True,
        stop_loss_valid=True,
    )

    assert result["action"] == "BLOCK"
    assert result["reasons"] == ["SAME_SYMBOL_POSITION_LIMIT"]

def test_missing_daily_loss_data_fails_closed():
    engine = RiskScoreEngine()

    result = engine.evaluate(
        risk_percent=0.50,
        daily_loss_percent=None,
        weekly_loss_percent=0.0,
        drawdown_percent=0.0,
        open_positions=0,
        same_symbol_positions=0,
        spread_ok=True,
        data_fresh=True,
        stop_loss_valid=True,
    )

    assert result["action"] == "BLOCK"
    assert result["risk_level"] == "HARD_BLOCK"
    assert result["reasons"] == ["MISSING_RISK_DATA"]

def test_risk_above_default_policy_requires_reduction():
    engine = RiskScoreEngine()

    result = engine.evaluate(
        risk_percent=0.75,
        daily_loss_percent=0.0,
        weekly_loss_percent=0.0,
        drawdown_percent=0.0,
        open_positions=0,
        same_symbol_positions=0,
        spread_ok=True,
        data_fresh=True,
        stop_loss_valid=True,
    )

    assert result["risk_level"] == "REDUCED_RISK"
    assert result["action"] == "REDUCE"
    assert result["reasons"] == ["PER_TRADE_POLICY_EXCEEDED"]

def test_assessment_includes_policy_version():
    engine = RiskScoreEngine()

    result = engine.evaluate(
        risk_percent=0.50,
        daily_loss_percent=0.0,
        weekly_loss_percent=0.0,
        drawdown_percent=0.0,
        open_positions=0,
        same_symbol_positions=0,
        spread_ok=True,
        data_fresh=True,
        stop_loss_valid=True,
    )

    assert result["policy_version"] == "atlas-risk-v1"

def test_assessment_includes_timestamp():
    engine = RiskScoreEngine()

    result = engine.evaluate(
        risk_percent=0.50,
        daily_loss_percent=0.0,
        weekly_loss_percent=0.0,
        drawdown_percent=0.0,
        open_positions=0,
        same_symbol_positions=0,
        spread_ok=True,
        data_fresh=True,
        stop_loss_valid=True,
    )

    assert "assessed_at" in result
    assert result["assessed_at"]
