def calculate_risk(
    direction: str,
    entry: float,
    stop_loss: float,
    take_profit: float,
    account_balance: float = 10000.0,
    risk_percent: float = 0.5,
    max_position_percent: float = 15.0,
) -> dict:

    direction = direction.upper()

    if direction not in {"LONG", "SHORT"}:
        return {
            "approved": False,
            "reason": "Trade direction must be LONG or SHORT.",
        }

    if entry <= 0 or stop_loss <= 0 or take_profit <= 0:
        return {
            "approved": False,
            "reason": "Prices must be greater than zero.",
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

    max_position_value = (
        account_balance * max_position_percent / 100
    )

    if position_value > max_position_value:
        position_size = max_position_value / entry
        position_value = max_position_value

        actual_risk = position_size * risk_per_unit
    else:
        actual_risk = risk_amount

    risk_reward = reward_per_unit / risk_per_unit

    approved = risk_reward >= 1.5

    if not approved:
        reason = "Risk/reward is below the minimum 1.5:1."
    else:
        reason = "Risk parameters acceptable for low-risk demo validation."

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
        "max_position_percent": max_position_percent,
    }
