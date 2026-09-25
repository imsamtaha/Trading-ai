from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.customer.contracts import MarketSnapshot
from app.customer.realtime.snapshot import snapshot_is_stale


class RescueAction(str, Enum):
    HOLD = "HOLD"
    REDUCE = "REDUCE"
    EXIT = "EXIT"
    PROTECT = "PROTECT"
    HALT = "HALT"


@dataclass(frozen=True)
class RescueDecision:
    action: RescueAction
    reason: str
    snapshot_id: str


class RescueAgent:
    def evaluate(self, position: dict, snapshot: MarketSnapshot) -> RescueDecision:
        if snapshot_is_stale(snapshot, max_age_seconds=60):
            return RescueDecision(RescueAction.HALT, "stale market feed", snapshot.snapshot_id)
        if snapshot.system.get("connector_ok") is not True:
            return RescueDecision(RescueAction.HALT, "connector unavailable", snapshot.snapshot_id)
        if float(position.get("unrealized_loss_pct", 0.0) or 0.0) >= 3.0:
            return RescueDecision(RescueAction.EXIT, "rapid drawdown threshold reached", snapshot.snapshot_id)
        direction = str(position.get("direction", "")).upper()
        trend = str(snapshot.market.get("trend", "")).lower()
        if (direction == "LONG" and trend == "bearish") or (direction == "SHORT" and trend == "bullish"):
            return RescueDecision(RescueAction.EXIT, "market reversal against position", snapshot.snapshot_id)
        if float(snapshot.market.get("spread_points", 0.0) or 0.0) >= 50.0:
            return RescueDecision(RescueAction.PROTECT, "spread anomaly", snapshot.snapshot_id)
        if float(snapshot.market.get("volatility", 0.0) or 0.0) >= 1.5:
            return RescueDecision(RescueAction.REDUCE, "volatility spike", snapshot.snapshot_id)
        return RescueDecision(RescueAction.HOLD, "position conditions stable", snapshot.snapshot_id)
