"""Broker-neutral, fail-closed safety governance for ATLAS paper research.

The module has no MT5 imports, sends no orders, and does not change active
Windows tasks, broker permissions, or the deployed website.
"""
from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from typing import Any, Mapping, Sequence

FRAMES = ("1h", "30m", "15m", "5m")
QUALITY_MAX = {
    "market_structure": 25,
    "momentum": 20,
    "timeframe_alignment": 20,
    "volatility": 15,
    "liquidity": 10,
    "signal_quality": 10,
    "risk_reward": 10,
}


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return result if isfinite(result) else None


def _epoch(value: Any) -> float | None:
    if isinstance(value, str):
        try:
            timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return timestamp.timestamp() if timestamp.tzinfo else None
    return _number(value)


def validate_candles(
    candles: Sequence[Mapping[str, Any]],
    *,
    interval_seconds: int,
    observed_at: float | None = None,
    max_age_seconds: int,
    min_bars: int = 5,
    bid: float | None = None,
    ask: float | None = None,
    max_spread_fraction: float | None = None,
) -> dict[str, Any]:
    """Reject non-finite OHLC, stale/future data, gaps, duplicate bars and spreads.

    Caller must supply CLOSED bars from the declared interval. A missing or
    malformed observation produces a reason code rather than an approval.
    """
    problems: set[str] = set()
    if interval_seconds <= 0 or max_age_seconds <= 0 or min_bars < 2:
        problems.add("INVALID_QUALITY_POLICY")
    if not isinstance(candles, (list, tuple)) or len(candles) < min_bars:
        problems.add("INSUFFICIENT_CANDLES")
    timestamps = []
    for candle in candles if isinstance(candles, (list, tuple)) else ():
        if not isinstance(candle, Mapping):
            problems.add("INVALID_CANDLE")
            continue
        stamp = _epoch(candle.get("time", candle.get("timestamp")))
        values = [_number(candle.get(field)) for field in ("open", "high", "low", "close")]
        if stamp is None or any(value is None or value <= 0 for value in values):
            problems.add("INVALID_CANDLE")
            continue
        op, high, low, close = values
        if low > min(op, close) or high < max(op, close) or low > high:
            problems.add("INCONSISTENT_OHLC")
        timestamps.append(stamp)
    count = len(candles) if isinstance(candles, (list, tuple)) else 0
    if len(timestamps) != count:
        problems.add("INCOMPLETE_CANDLE_TIMES")
    if len(set(timestamps)) != len(timestamps):
        problems.add("DUPLICATE_CANDLES")
    if any(second <= first for first, second in zip(timestamps, timestamps[1:])):
        problems.add("NON_MONOTONIC_CANDLES")
    if interval_seconds > 0 and any(
        second - first > interval_seconds * 1.1
        for first, second in zip(timestamps, timestamps[1:])
    ):
        problems.add("MISSING_CANDLES")
    now = _number(observed_at) if observed_at is not None else datetime.now(timezone.utc).timestamp()
    age = now - timestamps[-1] if timestamps and now is not None else None
    if age is None or age < -5 or age > max_age_seconds:
        problems.add("STALE_OR_FUTURE_DATA")
    if bid is not None or ask is not None or max_spread_fraction is not None:
        bid_n, ask_n, cap = _number(bid), _number(ask), _number(max_spread_fraction)
        if (bid_n is None or ask_n is None or cap is None
                or cap <= 0 or bid_n <= 0 or ask_n < bid_n):
            problems.add("INVALID_SPREAD_EVIDENCE")
        elif (ask_n - bid_n) / ((ask_n + bid_n) / 2) > cap:
            problems.add("SPREAD_TOO_WIDE")
    return {
        "valid": not problems,
        "reason_codes": sorted(problems),
        "bars_checked": count,
        "last_bar_age_seconds": round(age, 1) if age is not None else None,
    }


def score_decision(components: Mapping[str, Any] | None) -> dict[str, Any]:
    """Score evidence out of 110 points, not an estimated win probability."""
    if not isinstance(components, Mapping) or set(components) != set(QUALITY_MAX):
        return {"status": "UNAVAILABLE", "points": None, "maximum": 110, "probability": None}
    numeric = {name: _number(components[name]) for name in QUALITY_MAX}
    if any(numeric[name] is None or not 0 <= numeric[name] <= QUALITY_MAX[name] for name in QUALITY_MAX):
        return {"status": "INVALID", "points": None, "maximum": 110, "probability": None}
    return {
        "status": "SCORED",
        "points": round(sum(numeric.values()), 2),
        "maximum": sum(QUALITY_MAX.values()),
        "probability": None,
    }


def assess_paper_autonomy(evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate a non-executable PAPER candidate against all supplied evidence."""
    issues = set()
    if not isinstance(evidence, Mapping):
        evidence = {}
        issues.add("MISSING_EVIDENCE")
    mode = str(evidence.get("kill_switch", "HALTED")).upper()
    if mode not in {"ACTIVE", "DEFENSIVE", "HALTED"}:
        mode = "HALTED"
    if mode != "ACTIVE":
        issues.add("KILL_SWITCH_" + mode)
    for key in ("api_healthy", "snapshot_fresh", "data_quality_valid",
                "portfolio_exposure_ok", "correlation_ok"):
        if evidence.get(key) is not True:
            issues.add(key.upper() + "_NOT_VERIFIED")
    if evidence.get("event_risk") not in {"NORMAL", "LOW"}:
        issues.add("EVENT_RISK_UNACCEPTABLE")
    if evidence.get("volatility") != "NORMAL":
        issues.add("VOLATILITY_NOT_NORMAL")
    risk = evidence.get("senior_risk")
    if not isinstance(risk, Mapping) or risk.get("assessment") != "RISK_ACCEPTABLE":
        issues.add("SENIOR_RISK_VETO")
    frames = evidence.get("timeframes")
    direction = None
    if not isinstance(frames, Mapping) or set(frames) != set(FRAMES):
        issues.add("MTF_INCOMPLETE")
    else:
        directions = set()
        for frame in FRAMES:
            frame_evidence = frames.get(frame)
            if not isinstance(frame_evidence, Mapping) or frame_evidence.get("risk_approved") is not True:
                issues.add("MTF_RISK_VETO")
            directions.add(frame_evidence.get("direction") if isinstance(frame_evidence, Mapping) else None)
        if len(directions) == 1 and next(iter(directions)) in {"LONG", "SHORT"}:
            direction = next(iter(directions))
        else:
            issues.add("MTF_DISAGREEMENT")
    quality = score_decision(evidence.get("quality_components"))
    if quality["status"] != "SCORED":
        issues.add("QUALITY_NOT_VERIFIED")
    calibration = evidence.get("calibration")
    verified_probability = None
    if isinstance(calibration, Mapping):
        probability = _number(calibration.get("probability"))
        samples = _number(calibration.get("out_of_sample_samples"))
        if (probability is not None and 0 <= probability <= 1
                and samples is not None and samples > 0
                and calibration.get("validated_out_of_sample") is True
                and isinstance(calibration.get("profile_id"), str)
                and calibration.get("profile_id")):
            verified_probability = probability
    if verified_probability is None:
        issues.add("CALIBRATION_UNVERIFIED")
    return {
        "system": "Autonomous AI Trading System",
        "environment": "PAPER",
        "broker_execution_allowed": False,
        "paper_execution_performed": False,
        "state": mode,
        "decision": direction if not issues else "NO_TRADE",
        "paper_candidate_only": not issues,
        "reason_codes": sorted(issues) if issues else ["ALL_POLICY_GATES_PASSED"],
        "decision_quality": quality,
        "calibrated_probability": verified_probability,
    }


def record_assessment(
    assessment: Mapping[str, Any], *, symbol: str, snapshot_id: str, path: str
) -> dict[str, Any]:
    """Persist an audit entry, without a broker, training, or order side effect."""
    from app.intelligence.journal import SignalJournal

    if (not isinstance(assessment, Mapping)
            or assessment.get("environment") != "PAPER"
            or assessment.get("broker_execution_allowed") is not False
            or assessment.get("paper_execution_performed") is not False):
        raise ValueError("Only non-executable PAPER assessments may be audited")
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("symbol required")
    if not isinstance(snapshot_id, str) or not snapshot_id.strip():
        raise ValueError("snapshot_id required")
    return SignalJournal(path).append({
        "event": "AUTONOMY_SAFETY_ASSESSMENT",
        "symbol": symbol.strip().upper(),
        "snapshot_id": snapshot_id.strip(),
        "environment": "PAPER",
        "broker_execution_allowed": False,
        "state": assessment.get("state"),
        "decision": assessment.get("decision", "NO_TRADE"),
        "reason_codes": list(assessment.get("reason_codes") or []),
        "decision_quality": assessment.get("decision_quality"),
        "calibrated_probability": assessment.get("calibrated_probability"),
    })
