from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter

from app.customer.contracts import AgentStatus, AgentVerdict, MarketSnapshot, Signal
from app.customer.realtime.snapshot import snapshot_is_stale


class BaseAgent:
    name = "base"

    def _verdict(
        self,
        snapshot: MarketSnapshot,
        *,
        started: float,
        status: AgentStatus = AgentStatus.OK,
        signal: Signal = Signal.NEUTRAL,
        confidence: float = 0.0,
        evidence=(),
        blockers=(),
        fresh: bool = True,
        quality_score: float = 1.0,
    ) -> AgentVerdict:
        return AgentVerdict(
            agent=self.name,
            timestamp=datetime.now(timezone.utc),
            snapshot_id=snapshot.snapshot_id,
            status=status,
            signal=signal,
            confidence=max(0.0, min(1.0, float(confidence))),
            evidence=tuple(evidence),
            blockers=tuple(blockers),
            data_quality={"fresh": fresh, "score": max(0.0, min(1.0, quality_score))},
            latency_ms=max(0.0, (perf_counter() - started) * 1000),
        )

    @staticmethod
    def _stale(snapshot: MarketSnapshot) -> bool:
        return snapshot_is_stale(snapshot, max_age_seconds=60)
