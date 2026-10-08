from app.risk.manager import calculate_risk


def create_trade_candidate(
    signal: dict,
    technical: dict,
    account_balance: float = 10000.0,
) -> dict:

    direction = signal.get("direction")
    confidence = signal.get("confidence", 0)

    if direction not in {"LONG", "SHORT"}:
        return {
            "status": "NO_TRADE",
            "reason": "Signal is not actionable.",
            "signal": signal,
        }

    price = technical.get("price")
    atr = technical.get("indicators", {}).get("atr_14")

    if not price or not atr or atr <= 0:
        return {
            "status": "NO_TRADE",
            "reason": "Insufficient price or volatility data.",
            "signal": signal,
        }

    # Prototype stop/target model.
    # This will later be replaced by strategy-specific levels.
    if direction == "LONG":
        stop_loss = price - (1.5 * atr)
        take_profit = price + (3.0 * atr)
    else:
        stop_loss = price + (1.5 * atr)
        take_profit = price - (3.0 * atr)

    risk = calculate_risk(
        direction=direction,
        entry=price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        account_balance=account_balance,
    )

    if not risk["approved"]:
        return {
            "status": "REJECTED",
            "reason": risk["reason"],
            "signal": signal,
            "risk": risk,
        }

    return {
        "status": "TRADE_CANDIDATE",
        "direction": direction,
        "confidence": confidence,
        "entry": price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "signal": signal,
        "risk": risk,
    }
