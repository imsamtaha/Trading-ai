from math import isfinite, isclose

def calculate_risk(
    direction: str,
    entry: float,
    stop_loss: float,
    take_profit: float,
    account_balance: float = 10000.0,
    risk_percent: float = 1.0,
    max_position_percent: float = 25.0,
    daily_realized_pnl: float = 0.0,
    max_daily_loss_percent: float = 3.0,
    open_risk_percent: float = 0.0,
    max_total_open_risk_percent: float = 3.0,
    daily_start_capital: float | None = None,
) -> dict:
    """Apply deterministic ATLAS pre-trade risk controls.

    The defaults implement a conservative day-trading policy:
    - 1% requested risk per trade
    - 3% maximum realized daily loss
    - 3% maximum aggregate open risk
    - 25% maximum position value
    - minimum 1.5:1 reward/risk

    Existing callers remain backwards compatible because the added portfolio
    controls are optional and default to a clean account state.
    """

    daily_capital = account_balance if daily_start_capital is None else daily_start_capital
    values = (daily_capital, entry, stop_loss, take_profit, account_balance, risk_percent, max_position_percent,
              daily_realized_pnl, max_daily_loss_percent, open_risk_percent, max_total_open_risk_percent)
    if not all(isfinite(value) for value in values):
        return {"approved": False, "reason": "Risk inputs must be finite."}

    direction = direction.upper()

    if direction not in {"LONG", "SHORT"}:
        return {
            "approved": False,
            "reason": "Trade direction must be LONG or SHORT.",
        }

    if entry <= 0 or stop_loss <= 0 or take_profit <= 0:
        return {
            "approved": False,
            "reason": "Entry, stop-loss and take-profit must be greater than zero.",
        }

    if account_balance <= 0:
        return {
            "approved": False,
            "reason": "Account balance must be greater than zero.",
        }

    if risk_percent <= 0 or risk_percent > 2:
        return {
            "approved": False,
            "reason": "Risk percentage must be between 0 and 2.",
        }

    if max_daily_loss_percent <= 0:
        return {
            "approved": False,
            "reason": "Maximum daily loss percentage must be greater than zero.",
        }

    if open_risk_percent < 0 or max_total_open_risk_percent <= 0:
        return {
            "approved": False,
            "reason": "Open-risk limits are invalid.",
        }

    if daily_capital <= 0:
        return {"approved": False, "reason": "Start-of-day capital must be greater than zero."}

    daily_loss_amount = max(0.0, -daily_realized_pnl)
    daily_loss_percent = (daily_loss_amount / daily_capital) * 100

    if daily_loss_percent >= max_daily_loss_percent:
        return {
            "approved": False,
            "reason": "Daily loss limit reached. Trading must halt for the session.",
            "daily_loss_percent": round(daily_loss_percent, 4),
            "daily_start_capital": round(daily_capital, 2),
            "max_daily_loss_percent": max_daily_loss_percent,
        }

    if open_risk_percent + risk_percent > max_total_open_risk_percent:
        return {
            "approved": False,
            "reason": "Aggregate open-risk limit would be exceeded.",
            "open_risk_percent": round(open_risk_percent, 4),
            "requested_risk_percent": risk_percent,
            "max_total_open_risk_percent": max_total_open_risk_percent,
        }

    if direction == "LONG":
        if stop_loss >= entry:
            return {
                "approved": False,
                "reason": "LONG stop-loss must be below entry.",
            }

        if take_profit <= entry:
            return {
                "approved": False,
                "reason": "LONG take-profit must be above entry.",
            }

        risk_per_unit = entry - stop_loss
        reward_per_unit = take_profit - entry

    else:
        if stop_loss <= entry:
            return {
                "approved": False,
                "reason": "SHORT stop-loss must be above entry.",
            }

        if take_profit >= entry:
            return {
                "approved": False,
                "reason": "SHORT take-profit must be below entry.",
            }

        risk_per_unit = stop_loss - entry
        reward_per_unit = entry - take_profit

    if risk_per_unit <= 0 or reward_per_unit <= 0:
        return {
            "approved": False,
            "reason": "Risk and reward calculations are invalid.",
        }

    risk_amount = account_balance * (risk_percent / 100)
    position_size = risk_amount / risk_per_unit
    position_value = position_size * entry
    max_position_value = account_balance * max_position_percent / 100

    if position_value > max_position_value:
        position_size = max_position_value / entry
        position_value = max_position_value
        actual_risk = position_size * risk_per_unit
    else:
        actual_risk = risk_amount

    risk_reward = reward_per_unit / risk_per_unit
    approved = risk_reward >= 1.5 or isclose(risk_reward, 1.5, rel_tol=0, abs_tol=1e-12)

    if not approved:
        reason = "Risk/reward is below the minimum 1.5:1."
    else:
        reason = "Risk parameters acceptable."

    return {
        "approved": approved,
        "reason": reason,
        "direction": direction,
        "entry": round(entry, 8),
        "stop_loss": round(stop_loss, 8),
        "take_profit": round(take_profit, 8),
        "risk_reward": round(risk_reward, 2),
        "account_balance": round(account_balance, 2),
        "risk_percent": risk_percent,
        "maximum_risk_amount": round(risk_amount, 2),
        "actual_risk_amount": round(actual_risk, 2),
        "position_size": round(position_size, 8),
        "position_value": round(position_value, 2),
        "daily_start_capital": round(daily_capital, 2),
        "daily_realized_pnl": round(daily_realized_pnl, 2),
        "daily_loss_percent": round(daily_loss_percent, 4),
        "max_daily_loss_percent": max_daily_loss_percent,
        "open_risk_percent": round(open_risk_percent, 4),
        "max_total_open_risk_percent": max_total_open_risk_percent,
    }

