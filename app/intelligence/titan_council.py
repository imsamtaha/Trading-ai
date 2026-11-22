"""Unified SMC policy evaluation for reviewed evidence in PAPER mode."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool

POLICY = json.loads(Path(__file__).with_name("titan_policy.json").read_text(encoding="utf-8"))
LIMITS = POLICY["limits"]
WEIGHTS = POLICY["score_weights"]

Positive = Annotated[float, Field(strict=True, gt=0, allow_inf_nan=False)]
NonNegative = Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)]
Count = Annotated[int, Field(strict=True, ge=0)]
Note = Annotated[str, Field(min_length=1, max_length=1200)]


class TitanAccount(BaseModel):
    model_config = ConfigDict(extra="forbid")

    equity: Positive | None = None
    daily_loss_pct: NonNegative | None = None
    weekly_loss_pct: NonNegative | None = None
    monthly_drawdown_pct: NonNegative | None = None
    consecutive_losses: Count | None = None
    active_positions: Count | None = None


class TitanPriceLevels(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry: Positive
    stop_loss: Positive
    take_profit_1: Positive
    take_profit_2: Positive | None = None
    point_value: Positive = Field(description="Account-currency value of one price point per unit.")
    round_trip_cost_per_unit: NonNegative = Field(description="Estimated round-trip fees and slippage per unit in account currency.")


class TitanEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset: str | None = Field(default=None, max_length=32)
    current_price: Positive | None = None
    timestamp: datetime | None = None
    session: str | None = None
    charts: dict[str, StrictBool] = Field(default_factory=dict, max_length=5, description="Per-frame reviewer verdict for a clear labeled chart with visible structure and price scale.")
    higher_timeframe_bias: Literal["bullish", "bearish", "neutral"] | None = None
    timeframe_conflict: StrictBool | None = None
    regime: str | None = None
    direction: Literal["long", "short"] | None = None
    sweep_side: Literal["buy_side", "sell_side"] | None = None
    high_liquidity: StrictBool | None = None
    approved_major_crypto: StrictBool = False
    liquidity_analysis: Note | None = None
    liquidity_target: Note | None = None
    smc_analysis: Note | None = None
    checks: dict[str, StrictBool] = Field(default_factory=dict, max_length=7, description="Directional confirmations keyed by score_weights in the TITAN policy.")
    news_risk: Literal["low", "medium", "high", "unknown"] = "unknown"
    news_cleared: StrictBool | None = None
    session_cleared: StrictBool | None = None
    account: TitanAccount = Field(default_factory=TitanAccount)
    levels: TitanPriceLevels | None = None
    requested_risk_pct: Positive = LIMITS["preferred_risk_pct"]
    confidence_pct: Annotated[float, Field(strict=True, ge=0, le=100, allow_inf_nan=False)] | None = None


def evaluate_titan(evidence: TitanEvidence) -> dict:
    asset = (evidence.asset or "").strip().upper()
    reasons = []
    stamp = evidence.timestamp
    if stamp is None or stamp.utcoffset() is None or stamp > datetime.now(timezone.utc):
        reasons.append("Provide a valid observation timestamp with timezone.")
    if not asset or evidence.current_price is None:
        reasons.append("Provide the asset and current price.")
    if (not asset or evidence.high_liquidity is not True
            or (asset not in POLICY["primary_assets"] and not evidence.approved_major_crypto)):
        reasons.append("Confirm an approved high-liquidity crypto market.")
    missing_charts = [frame for frame in POLICY["timeframes"] if evidence.charts.get(frame) is not True]
    if missing_charts:
        reasons.append("Request better charts for: " + ", ".join(missing_charts) + ".")
    if evidence.regime not in POLICY["regimes"] or evidence.regime == "manipulation":
        reasons.append("Market regime is unclear or manipulation was flagged.")
    if evidence.session not in POLICY["sessions"] or evidence.session_cleared is not True:
        reasons.append("Wait for a preferred session with acceptable trading conditions.")
    if stamp is not None and stamp.utcoffset() is not None and stamp.astimezone(timezone.utc).weekday() >= 5:
        reasons.append("Weekend conditions are excluded.")
    expected_bias, expected_sweep = {
        "long": ("bullish", "sell_side"), "short": ("bearish", "buy_side"),
    }.get(evidence.direction, (None, None))
    if expected_bias is None or evidence.higher_timeframe_bias != expected_bias or evidence.timeframe_conflict is not False:
        reasons.append("Confirm higher-timeframe alignment and resolve any conflicts.")
    if expected_sweep is None or evidence.sweep_side != expected_sweep:
        reasons.append("Confirm the liquidity sweep on the correct side.")
    if not all((evidence.liquidity_analysis, evidence.liquidity_target, evidence.smc_analysis)):
        reasons.append("Record the liquidity map, target and SMC evidence.")
    confirmed = {key: evidence.checks.get(key) is True for key in WEIGHTS}
    confirmed["liquidity_sweep"] &= expected_sweep is not None and evidence.sweep_side == expected_sweep
    score = sum(weight for key, weight in WEIGHTS.items() if confirmed[key])
    grade = next(grade for grade, floor in POLICY["grades"].items() if score >= floor)
    incomplete = [key for key, checked in confirmed.items() if not checked]
    if incomplete:
        reasons.append("Complete directional confirmation for: " + ", ".join(incomplete) + ".")
    if grade not in {"S", "A"}:
        reasons.append("Setup grade is below A.")
    if evidence.news_risk not in {"low", "medium"} or evidence.news_cleared is not True:
        reasons.append("News review is missing, uncertain or high risk.")

    account = evidence.account
    account_checks = {
        "daily_loss_pct": account.daily_loss_pct,
        "weekly_loss_pct": account.weekly_loss_pct,
        "monthly_drawdown_pct": account.monthly_drawdown_pct,
        "consecutive_losses": account.consecutive_losses,
        "max_positions": account.active_positions,
    }
    if account.equity is None or any(value is None for value in account_checks.values()):
        reasons.append("Provide the paper account equity, losses, drawdown and active positions.")
    stopped = [key for key, value in account_checks.items() if value is not None and value >= LIMITS[key]]
    if stopped:
        reasons.append("Capital preservation limit reached: " + ", ".join(stopped) + ".")
    if evidence.requested_risk_pct > LIMITS["max_risk_pct"]:
        reasons.append("Requested risk exceeds the per-trade maximum.")

    levels = evidence.levels
    rr = loss = None
    if levels is None or evidence.direction is None:
        reasons.append("Provide directional entry, stop, first target and cost assumptions.")
    else:
        sign = 1 if evidence.direction == "long" else -1
        stop_distance = sign * (levels.entry - levels.stop_loss)
        target_distance = sign * (levels.take_profit_1 - levels.entry)
        second_target_valid = levels.take_profit_2 is None or sign * (levels.take_profit_2 - levels.take_profit_1) > 0
        if stop_distance <= 0 or target_distance <= 0 or not second_target_valid:
            reasons.append("Correct the directional order of the stop, entry and targets.")
        else:
            loss = stop_distance * levels.point_value + levels.round_trip_cost_per_unit
            reward = target_distance * levels.point_value - levels.round_trip_cost_per_unit
            if loss <= 0 or not isfinite(loss) or not isfinite(reward) or not isfinite(reward / loss):
                reasons.append("Use trade levels and costs within the supported numeric range.")
            else:
                rr = reward / loss
                if rr < LIMITS["minimum_rr"]:
                    reasons.append("First target is below the required 1:3 reward after costs.")

    risk_budget = max_units = None
    if not reasons:
        risk_budget = account.equity * (evidence.requested_risk_pct / 100)
        max_units = risk_budget / loss
        if max_units <= 0 or not isfinite(max_units):
            reasons.append("Paper position size is outside the supported numeric range.")
            risk_budget = max_units = None
    decision = "WAIT" if reasons else ("BUY" if evidence.direction == "long" else "SELL")
    return {
        "council": POLICY["name"],
        "version": POLICY["version"],
        "mode": POLICY["mode"],
        "broker_execution_allowed": False,
        "asset": asset or None,
        "current_price": evidence.current_price,
        "timestamp": stamp.isoformat() if stamp else None,
        "session": evidence.session,
        "market_regime": evidence.regime,
        "higher_timeframe_bias": evidence.higher_timeframe_bias,
        "liquidity_analysis": evidence.liquidity_analysis,
        "liquidity_target": evidence.liquidity_target,
        "sweep_side": evidence.sweep_side,
        "smc_analysis": evidence.smc_analysis,
        "confirmations": confirmed,
        "news_risk": evidence.news_risk,
        "setup_score": score,
        "trade_grade": grade,
        "trade_decision": decision,
        "entry": levels.entry if not reasons else None,
        "stop_loss": levels.stop_loss if not reasons else None,
        "take_profit_1": levels.take_profit_1 if not reasons else None,
        "take_profit_2": levels.take_profit_2 if not reasons else None,
        "reward_to_risk": rr,
        "position_risk_pct": evidence.requested_risk_pct if not reasons else None,
        "risk_budget": risk_budget,
        "max_units_before_lot_rounding": max_units,
        "confidence_pct": evidence.confidence_pct,
        "capital_preservation_verdict": "STOP" if stopped else ("WAIT" if reasons else "PAPER_REVIEW"),
        "reasoning": reasons or ["All required TITAN checks passed on the supplied evidence. Review the paper setup before recording it."],
    }
