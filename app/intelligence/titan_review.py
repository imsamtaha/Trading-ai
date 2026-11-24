"""Review a supplied weekly or monthly slice of settled TITAN paper trades."""
from collections import Counter
from datetime import datetime, timezone
from math import isfinite
from statistics import mean
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StringConstraints, field_validator

from app.intelligence.titan_council import POLICY


Amount = Annotated[float, Field(strict=True, allow_inf_nan=False, ge=-1e100, le=1e100)]
PositiveAmount = Annotated[float, Field(strict=True, allow_inf_nan=False, ge=1e-100, le=1e100)]
Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
ProcessScore = Annotated[int, Field(strict=True, ge=0, le=10)]


class TitanSettledTrade(BaseModel):
    model_config = ConfigDict(extra="forbid")

    settled_at: datetime
    setup: Label
    session: Label
    pnl: Amount
    initial_risk: PositiveAmount
    rule_compliant: StrictBool
    process_scores: list[ProcessScore] = Field(min_length=6, max_length=6)
    mistakes: list[Label] = Field(default_factory=list, max_length=12)
    lessons: list[Label] = Field(default_factory=list, max_length=12)

    @field_validator("settled_at")
    @classmethod
    def check_timestamp(cls, value: datetime) -> datetime:
        if value.utcoffset() is None or value > datetime.now(timezone.utc):
            raise ValueError("settled_at must have a timezone and cannot be in the future")
        return value


class TitanReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: Literal["weekly", "monthly"]
    opening_equity: PositiveAmount
    trades: list[TitanSettledTrade] = Field(default_factory=list, max_length=2000)


def review_titan(payload: TitanReview) -> dict:
    trades = sorted(payload.trades, key=lambda trade: trade.settled_at)
    pnls = [trade.pnl for trade in trades]
    realized_r = [trade.pnl / trade.initial_risk for trade in trades]
    wins = [pnl for pnl in pnls if pnl > 0]
    losses = [-pnl for pnl in pnls if pnl < 0]
    gross_loss = sum(losses)
    profit_factor = sum(wins) / gross_loss if gross_loss else None
    peak = equity = payload.opening_equity
    drawdown = 0.0
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        drawdown = max(drawdown, (peak - equity) / peak * 100)

    by_setup: dict[str, list[float]] = {}
    by_session: dict[str, list[float]] = {}
    for trade, r_multiple in zip(trades, realized_r):
        by_setup.setdefault(trade.setup, []).append(r_multiple)
        by_session.setdefault(trade.session, []).append(r_multiple)

    setup_performance = {key: {"trades": len(values), "average_r": mean(values)} for key, values in by_setup.items()}
    session_performance = {key: {"trades": len(values), "average_r": mean(values)} for key, values in by_session.items()}
    ranked = sorted(trades, key=lambda trade: trade.pnl / trade.initial_risk, reverse=True)

    def trade_summary(trade: TitanSettledTrade) -> dict:
        return {
            "setup": trade.setup,
            "session": trade.session,
            "settled_at": trade.settled_at.isoformat(),
            "pnl": trade.pnl,
            "realized_r": trade.pnl / trade.initial_risk,
            "rule_compliant": trade.rule_compliant,
        }

    violations = sum(not trade.rule_compliant for trade in trades)
    mistakes = Counter(mistake for trade in trades for mistake in set(trade.mistakes))
    result = {
        "mode": POLICY["mode"],
        "period": payload.period,
        "settled_trades": len(trades),
        "win_rate_pct": 100 * len(wins) / len(trades) if trades else None,
        "average_realized_r": mean(realized_r) if trades else None,
        "profit_factor": profit_factor if profit_factor is not None and isfinite(profit_factor) else None,
        "max_drawdown_pct": drawdown if trades else None,
        "risk_compliance_pct": 100 * (len(trades) - violations) / len(trades) if trades else None,
        "rule_violations": violations,
        "average_process_score_out_of_60": mean(sum(trade.process_scores) for trade in trades) if trades else None,
        "best_setup_by_average_r": max(by_setup, key=lambda key: mean(by_setup[key]), default=None),
        "worst_setup_by_average_r": min(by_setup, key=lambda key: mean(by_setup[key]), default=None),
        "recorded_lessons": list(dict.fromkeys(lesson for trade in trades for lesson in trade.lessons)),
    }
    if payload.period == "monthly":
        result.update(
            capital_growth=sum(pnls) if trades else None,
            setup_performance=setup_performance,
            session_performance=session_performance,
            top_winners=[trade_summary(trade) for trade in ranked if trade.pnl > 0][:3],
            top_losers=[trade_summary(trade) for trade in reversed(ranked) if trade.pnl < 0][:3],
            most_common_mistake=min(mistakes, key=lambda key: (-mistakes[key], key), default=None),
        )
    return result
