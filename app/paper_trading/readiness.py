"""Evidence-based readiness checks for ATLAS forward-demo trading."""
from __future__ import annotations

from typing import Any


DEFAULT_MIN_CLOSED_TRADES = 25
DEFAULT_MAX_DRAWDOWN_PERCENT = 10.0
DEFAULT_MIN_PROFIT_FACTOR = 1.10


def evaluate_demo_readiness(
    closed_trades: list[dict[str, Any]],
    *,
    min_closed_trades: int = DEFAULT_MIN_CLOSED_TRADES,
    max_drawdown_percent: float = DEFAULT_MAX_DRAWDOWN_PERCENT,
    min_profit_factor: float = DEFAULT_MIN_PROFIT_FACTOR,
) -> dict[str, Any]:
    """Evaluate evidence only; this function never enables live trading."""
    pnl = [float(trade.get("risk_normalized_pnl", 0.0) or 0.0) for trade in closed_trades]
    wins = [value for value in pnl if value > 0]
    losses = [value for value in pnl if value < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = gross_profit / gross_loss if gross_loss else (float("inf") if gross_profit else 0.0)
    expectancy = sum(pnl) / len(pnl) if pnl else 0.0
    win_rate = (len(wins) / len(pnl) * 100.0) if pnl else 0.0

    equity = 0.0
    peak = 0.0
    maximum_drawdown = 0.0
    for value in pnl:
        equity += value
        peak = max(peak, equity)
        maximum_drawdown = max(maximum_drawdown, peak - equity)

    total_risk = sum(abs(float(trade.get("risk_amount", 0.0) or 0.0)) for trade in closed_trades)
    max_drawdown_percent_actual = (
        maximum_drawdown / total_risk * 100.0 if total_risk > 0 else 0.0
    )

    checks = {
        "minimum_closed_trades": len(pnl) >= min_closed_trades,
        "positive_expectancy": expectancy > 0,
        "minimum_profit_factor": profit_factor >= min_profit_factor,
        "maximum_drawdown": max_drawdown_percent_actual <= max_drawdown_percent,
    }
    ready = all(checks.values())
    return {
        "ready_for_live_review": ready,
        "automatic_live_activation": False,
        "closed_trades": len(pnl),
        "required_closed_trades": min_closed_trades,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_percent": round(win_rate, 2),
        "expectancy": round(expectancy, 4),
        "profit_factor": round(profit_factor, 4) if profit_factor != float("inf") else "INF",
        "max_drawdown_percent_of_total_risk": round(max_drawdown_percent_actual, 2),
        "checks": checks,
        "decision": "REVIEW_REQUIRED" if ready else "CONTINUE_FORWARD_DEMO",
    }
