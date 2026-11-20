"""ATLAS nine-seat council: isolated, PAPER-only *decision-support* contract.

This module never fetches market prices, calls an LLM, executes an order,
modifies Council weights, or claims simulated fills occurred. It validates
independently submitted seat reports and packages a PAPER-only draft.

The seat coordinator is deliberately separate from the existing production
Council; adopting this contract never enables real/demo broker execution.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from math import isfinite
from typing import Any, Mapping

INITIAL_SEATS = ("macro", "market_structure", "quant", "news_sentiment")
RISK_CHECKS = ("daily_loss", "total_open_risk", "correlation", "position_size", "event_exposure")
VALID_TIMEFRAMES = {"5m", "15m", "30m", "1h"}
SUPPORTED_ASSETS = {
    "XAUUSD": "gold",
    "GOLD": "gold",
    "XAGUSD": "commodity",
    "SILVER": "commodity",
    "NGAS": "commodity",
    "XNGUSD": "commodity",
    "NATGAS": "commodity",
    "GAS": "commodity",
    "EURUSD": "fx",
    "US500": "equity_index",
    "US30": "equity_index",
    "NAS100": "equity_index",
    "AAPL": "equity", "MSFT": "equity", "NVDA": "equity",
    "AMZN": "equity", "GOOGL": "equity", "META": "equity",
    "TSLA": "equity", "JPM": "equity", "BRK.B": "equity",
    "XRP": "crypto", "SOL": "crypto",
    "XRPUSD": "crypto", "SOLUSD": "crypto",
    "XRPUSDT": "crypto", "SOLUSDT": "crypto",
}
VALID_RISK = {"APPROVE", "VETO", "CONDITIONAL"}
VALID_VERDICTS = {"LONG", "SHORT", "NO TRADE", "VETOED"}


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must contain a non-empty written assessment")
    return value.strip()


def _bounded_number(value: Any, field: str, low: float, high: float) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be numeric")
    try:
        n = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not isfinite(n) or not low <= n <= high:
        raise ValueError(f"{field} must be finite and in [{low}, {high}]")
    return n


def _stamp(value: str) -> str:
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise ValueError("timestamp must be ISO-8601") from exc
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return stamp.isoformat()


def classify_instrument(symbol: str) -> str:
    key = _text(symbol, "instrument").upper()
    if key not in SUPPORTED_ASSETS:
        raise ValueError("Unsupported instrument; configure coverage explicitly")
    return SUPPORTED_ASSETS[key]


def core_first(recommendations: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Gold/equity precedes satellite crypto; never show low-conviction crypto."""
    visible = [
        item for item in recommendations
        if item.get("mode") == "paper"
        and (
            item.get("asset_class") != "crypto"
            or item.get("conviction") == 5
        )
    ]
    order = {"gold": 0, "equity_index": 1, "equity": 1, "commodity": 2, "fx": 3, "crypto": 4}
    return sorted(visible, key=lambda item: order.get(str(item.get("asset_class")), 99))


@dataclass
class NineSeatPaperCouncil:
    instrument: str
    timeframe: str
    timestamp: str
    snapshot_id: str
    # Verification must come from the platform, not LLM text.
    verified_market_snapshot: bool = False
    _initial: dict[str, dict[str, Any]] = field(default_factory=dict, init=False, repr=False)
    _risk: dict[str, Any] | None = field(default=None, init=False, repr=False)
    _execution: dict[str, Any] | None = field(default=None, init=False, repr=False)
    _red_team: dict[str, Any] | None = field(default=None, init=False, repr=False)
    _chair: dict[str, Any] | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.instrument = _text(self.instrument, "instrument").upper()
        self.asset_class = classify_instrument(self.instrument)
        if self.timeframe not in VALID_TIMEFRAMES:
            raise ValueError("1m is entry-timing only; standalone bias requires 5m/15m/30m/1h")
        self.timestamp = _stamp(self.timestamp)
        self.snapshot_id = _text(self.snapshot_id, "snapshot_id")

    def submit_initial(self, seat: str, report: Mapping[str, Any], *, snapshot_id: str) -> None:
        """Each initial seat submits once; no other seat data is passed in."""
        if self._risk is not None:
            raise ValueError("Initial reports are sealed before Risk assessment")
        if seat not in INITIAL_SEATS or seat in self._initial:
            raise ValueError("Invalid or duplicate independent seat report")
        if snapshot_id != self.snapshot_id:
            raise ValueError("Mismatched market snapshot")
        if not isinstance(report, Mapping):
            raise ValueError("Seat report must be a mapping")
        data = dict(report)
        required = {
            "macro": ("bias", "driver", "horizon"),
            "market_structure": ("read", "invalidation", "higher_timeframe"),
            "quant": ("base_rate_source", "regime_note"),
            "news_sentiment": ("event_risk", "sentiment_skew"),
        }[seat]
        for name in required:
            data[name] = _text(data.get(name), f"{seat}.{name}")
        if seat == "quant":
            samples = data.get("sample_size")
            if isinstance(samples, bool) or not isinstance(samples, int) or samples < 0:
                raise ValueError("quant.sample_size must be a non-negative integer")
            data["confidence"] = _bounded_number(data.get("confidence"), "quant.confidence", 0, 1)
            data["average_rr"] = _bounded_number(data.get("average_rr"), "quant.average_rr", 0, 100)
            data["win_rate"] = _bounded_number(data.get("win_rate"), "quant.win_rate", 0, 1)
        else:
            if "confidence" in data:
                data["confidence"] = _bounded_number(data["confidence"], f"{seat}.confidence", 0, 1)
        self._initial[seat] = data

    def submit_risk(self, report: Mapping[str, Any]) -> None:
        if set(self._initial) != set(INITIAL_SEATS) or self._risk is not None:
            raise ValueError("All four independent seats must submit before one Risk verdict")
        data = dict(report)
        status = _text(data.get("status"), "risk.status").upper()
        if status not in VALID_RISK:
            raise ValueError("Risk must be APPROVE, VETO or CONDITIONAL")
        data["status"] = status
        data["reason"] = _text(data.get("reason"), "risk.reason")
        if status == "VETO":
            data["minimum_change"] = _text(data.get("minimum_change"), "risk.minimum_change")
        elif status == "CONDITIONAL":
            data["conditions"] = _text(data.get("conditions"), "risk.conditions")
        else:
            checks = data.get("checks")
            if (not isinstance(checks, Mapping) or
                    any(checks.get(name) != "PASS" for name in RISK_CHECKS)):
                raise ValueError("Risk APPROVE requires explicit PASS for every account-level check")
            data["approved_position_size_pct"] = _bounded_number(
                data.get("approved_position_size_pct"), "risk.approved_position_size_pct", 0, 100
            )
        self._risk = data

    def submit_execution(self, report: Mapping[str, Any]) -> None:
        if not self._risk or self._risk["status"] != "APPROVE":
            raise ValueError("Execution plan requires explicit Risk APPROVE")
        if self._execution is not None:
            raise ValueError("Duplicate execution plan")
        data = dict(report)
        data["plan"] = _text(data.get("plan"), "execution.plan")
        data["hazards"] = _text(data.get("hazards"), "execution.hazards")
        if str(data.get("order_type", "")).lower() not in {"market", "limit", "stop"}:
            raise ValueError("Execution order_type must be market, limit or stop (PAPER only)")
        data["entry"] = _bounded_number(data.get("entry"), "execution.entry", 0.0000001, 1e15)
        data["stop"] = _bounded_number(data.get("stop"), "execution.stop", 0.0000001, 1e15)
        targets = data.get("take_profit")
        if not isinstance(targets, list) or not targets:
            raise ValueError("At least one PAPER take-profit level required")
        data["take_profit"] = [
            _bounded_number(value, "execution.take_profit", 0.0000001, 1e15)
            for value in targets
        ]
        self._execution = data

    def submit_red_team(self, report: Mapping[str, Any]) -> None:
        if self._risk is None or self._risk["status"] != "APPROVE" or self._execution is None:
            raise ValueError("Red Team challenges only after Risk approval and an execution plan")
        if self._red_team is not None:
            raise ValueError("Duplicate Red Team report")
        data = dict(report)
        data["objection"] = _text(data.get("objection"), "red_team.objection")
        data["failure_condition"] = _text(data.get("failure_condition"), "red_team.failure_condition")
        if data["objection"].casefold() in {"no objection", "none", "لا اعتراض"}:
            _text(data.get("justification"), "red_team.justification")
        self._red_team = data

    def submit_chair(self, report: Mapping[str, Any]) -> None:
        if self._risk is None or self._chair is not None:
            raise ValueError("Chair waits for the Risk verdict and decides only once")
        if self._risk["status"] == "APPROVE" and (self._execution is None or self._red_team is None):
            raise ValueError("Chair needs execution and Red Team challenge first")
        data = dict(report)
        verdict = _text(data.get("verdict"), "chair.verdict").upper()
        if verdict not in VALID_VERDICTS:
            raise ValueError("Unsupported Chair verdict")
        data["verdict"] = verdict
        conviction = data.get("conviction")
        if isinstance(conviction, bool) or not isinstance(conviction, int) or not 1 <= conviction <= 5:
            raise ValueError("Chair conviction must be an integer from 1 to 5")
        data["rationale"] = _text(data.get("rationale"), "chair.rationale")
        drivers = data.get("drivers")
        if not isinstance(drivers, list) or not drivers or any(
                driver not in INITIAL_SEATS for driver in drivers):
            raise ValueError("Chair rationale must cite valid independent seat drivers")
        if verdict in {"LONG", "SHORT"} and self._risk["status"] != "APPROVE":
            raise ValueError("Chair cannot overrule Risk")
        if self._risk["status"] == "VETO" and verdict != "VETOED":
            raise ValueError("Risk veto must be reported as VETOED")
        if self._risk["status"] != "VETO" and verdict == "VETOED":
            raise ValueError("Chair cannot invent a Risk veto")
        if self._risk["status"] == "CONDITIONAL" and verdict != "NO TRADE":
            raise ValueError("Conditions not satisfied: final verdict must be NO TRADE")
        if self.asset_class == "crypto" and conviction < 5 and verdict in {"LONG", "SHORT"}:
            raise ValueError("Satellite crypto requires conviction 5/5")
        if verdict in {"LONG", "SHORT"}:
            data["position_size_pct"] = _bounded_number(
                data.get("position_size_pct"), "chair.position_size_pct", 0, 100
            )
            if data["position_size_pct"] > self._risk["approved_position_size_pct"]:
                raise ValueError("Chair proposed size exceeds approved Risk limit")
            entry = self._execution["entry"]
            stop = self._execution["stop"]
            targets = self._execution["take_profit"]
            if verdict == "LONG" and not (stop < entry and all(target > entry for target in targets)):
                raise ValueError("PAPER LONG price-level geometry invalid")
            if verdict == "SHORT" and not (stop > entry and all(target < entry for target in targets)):
                raise ValueError("PAPER SHORT price-level geometry invalid")
            if not self.verified_market_snapshot:
                raise ValueError("No directional paper proposal without verified snapshot")
        else:
            data["position_size_pct"] = 0.0
        self._chair = data

    def finalize(self) -> dict[str, Any]:
        if self._chair is None or self._risk is None:
            raise ValueError("Chair verdict and Risk assessment are required")
        risk = self._risk
        chair = self._chair
        verdict = chair["verdict"]
        if not self.verified_market_snapshot and verdict in {"LONG", "SHORT"}:
            raise ValueError("Unverified market context cannot produce directional proposal")
        if risk["status"] == "VETO":
            verdict = "VETOED"
        if risk["status"] == "CONDITIONAL":
            verdict = "NO TRADE"
        active = verdict in {"LONG", "SHORT"}
        exec_data = self._execution or {}
        if not active:
            exec_data = {}
        note = chair["rationale"]
        if risk["status"] == "VETO":
            note += " | Risk veto: " + risk["reason"] + ". Minimum change: " + risk["minimum_change"]
        elif risk["status"] == "CONDITIONAL":
            note += " | Not yet approved: " + risk["conditions"]
        if self._initial["quant"]["sample_size"] < 30:
            note += " | Quant n<30: anecdotal, not statistically reliable."
        if not self.verified_market_snapshot:
            note += " | MARKET DATA UNVERIFIED: no actionable proposal."
        return {
            "instrument": self.instrument,
            "asset_class": self.asset_class,
            "timeframe": self.timeframe,
            "timestamp": self.timestamp,
            "mode": "paper",
            "verdict": verdict,
            "conviction": chair["conviction"],
            "position_size_pct": chair["position_size_pct"] if active else 0.0,
            "entry": exec_data.get("entry") if active else None,
            "stop": exec_data.get("stop") if active else None,
            "take_profit": list(exec_data.get("take_profit", [])) if active else [],
            "seats": {
                "macro": {
                    "bias": self._initial["macro"]["bias"],
                    "driver": self._initial["macro"]["driver"],
                },
                "market_structure": {
                    "read": self._initial["market_structure"]["read"],
                    "invalidation": self._initial["market_structure"]["invalidation"],
                },
                "quant": {
                    "confidence": self._initial["quant"]["confidence"],
                    "sample_size": self._initial["quant"]["sample_size"],
                },
                "risk": {
                    "status": risk["status"],
                    "reason": (
                        risk["reason"] + " | Minimum change: " + risk["minimum_change"]
                        if risk["status"] == "VETO" else risk["reason"]
                    ),
                },
                "execution": {"plan": exec_data.get("plan", "") if active else ""},
                "news_sentiment": {
                    "event_risk": self._initial["news_sentiment"]["event_risk"],
                    "sentiment_skew": self._initial["news_sentiment"]["sentiment_skew"],
                },
                "red_team": {
                    "objection": (
                        self._red_team["objection"] + " | Failure condition: " +
                        self._red_team["failure_condition"]
                        if self._red_team else ""
                    ),
                },
            },
            "chair_rationale": "SIMULATED/PAPER RECOMMENDATION — " + note,
        }


def evaluator_scorecard(outcomes: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Weekly, retrospective only: use *settled* PAPER results, no voting.

    Return sample sizes and directional hit rates by asset class and
    Chair conviction without treating non-settled records as actual fills.
    """
    samples: list[Mapping[str, Any]] = []
    for row in outcomes:
        if (row.get("mode") != "paper" or
                row.get("verdict") not in {"LONG", "SHORT"} or
                row.get("settled") is not True or
                not isinstance(row.get("correct"), bool)):
            continue
        score = row.get("conviction")
        if isinstance(score, int) and not isinstance(score, bool) and 1 <= score <= 5:
            samples.append(row)
    bins: dict[str, dict[str, int]] = {}
    by_asset: dict[str, dict[str, int]] = {}
    for row in samples:
        score = row["conviction"]
        k = str(score)
        category = str(row.get("asset_class", "unknown"))
        for dest, label in ((bins, k), (by_asset, category)):
            cell = dest.setdefault(label, {"n": 0, "correct": 0})
            cell["n"] += 1
            cell["correct"] += int(row["correct"])
    def format_rates(group: dict[str, dict[str, int]]) -> dict[str, dict[str, Any]]:
        return {key: {"n": v["n"], "hit_rate": round(v["correct"] / v["n"], 4)}
                for key, v in sorted(group.items())}
    return {
        "mode": "paper",
        "cadence": "weekly",
        "status": "REVIEW" if len(samples) >= 30 else "INSUFFICIENT_SETTLED_PAPER_SAMPLES",
        "settled_paper_count": len(samples),
        "conviction_calibration": format_rates(bins),
        "asset_class_scorecard": format_rates(by_asset),
        "evaluator_votes": False,
        "broker_execution_allowed": False,
    }
