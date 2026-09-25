from __future__ import annotations

from dataclasses import dataclass

from app.customer.contracts import Decision, DecisionCandidate, MarketSnapshot, Mode


@dataclass(frozen=True)
class TradeIntent:
    customer_id: str
    account_id: str
    snapshot_id: str
    mode: Mode
    symbol: str
    direction: str
    entry: float
    stop_loss: float
    take_profit: float
    confidence: float


class TraderAgent:
    def build_intent(
        self,
        snapshot: MarketSnapshot,
        decision: DecisionCandidate,
        *,
        entry: float,
        stop_loss: float,
        take_profit: float,
    ) -> TradeIntent:
        if decision.snapshot_id != snapshot.snapshot_id:
            raise ValueError("decision and snapshot identity mismatch")
        if decision.decision not in {Decision.BUY, Decision.SELL}:
            raise ValueError("decision is not actionable")
        direction = "LONG" if decision.decision is Decision.BUY else "SHORT"
        if direction == "LONG" and not (stop_loss < entry < take_profit):
            raise ValueError("LONG requires stop_loss < entry < take_profit")
        if direction == "SHORT" and not (take_profit < entry < stop_loss):
            raise ValueError("SHORT requires take_profit < entry < stop_loss")
        return TradeIntent(
            customer_id=snapshot.customer_id,
            account_id=snapshot.account_id,
            snapshot_id=snapshot.snapshot_id,
            mode=snapshot.mode,
            symbol=snapshot.symbol,
            direction=direction,
            entry=float(entry),
            stop_loss=float(stop_loss),
            take_profit=float(take_profit),
            confidence=float(decision.confidence),
        )
