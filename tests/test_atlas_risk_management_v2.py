from app.risk.manager import calculate_risk


def test_default_one_percent_risk_is_approved_for_valid_trade():
    result = calculate_risk(
        direction="LONG",
        entry=100.0,
        stop_loss=99.0,
        take_profit=102.0,
        account_balance=10_000.0,
    )

    assert result["approved"] is True
    assert result["risk_percent"] == 1.0
    assert result["maximum_risk_amount"] == 100.0


def test_daily_loss_gate_halts_trading_at_three_percent():
    result = calculate_risk(
        direction="LONG",
        entry=100.0,
        stop_loss=99.0,
        take_profit=102.0,
        account_balance=10_000.0,
        daily_realized_pnl=-300.0,
    )

    assert result["approved"] is False
    assert result["reason"] == "Daily loss limit reached. Trading must halt for the session."
    assert result["daily_loss_percent"] == 3.0


def test_open_risk_gate_rejects_trade_that_exceeds_portfolio_limit():
    result = calculate_risk(
        direction="SHORT",
        entry=100.0,
        stop_loss=101.0,
        take_profit=98.0,
        account_balance=10_000.0,
        risk_percent=1.0,
        open_risk_percent=2.5,
        max_total_open_risk_percent=3.0,
    )

    assert result["approved"] is False
    assert result["reason"] == "Aggregate open-risk limit would be exceeded."


def test_stop_loss_remains_mandatory_and_directionally_valid():
    result = calculate_risk(
        direction="LONG",
        entry=100.0,
        stop_loss=100.0,
        take_profit=102.0,
    )

    assert result["approved"] is False
    assert result["reason"] == "LONG stop-loss must be below entry."


def test_minimum_reward_risk_gate_is_preserved():
    result = calculate_risk(
        direction="LONG",
        entry=100.0,
        stop_loss=99.0,
        take_profit=101.0,
    )

    assert result["approved"] is False
    assert result["reason"] == "Risk/reward is below the minimum 1.5:1."



def test_risk_accepts_exact_reward_risk_boundary():
    result = calculate_risk(direction="LONG", entry=1.1002, stop_loss=1.099,
                            take_profit=1.102, account_balance=10000, risk_percent=0.25)
    assert result["approved"] is True
