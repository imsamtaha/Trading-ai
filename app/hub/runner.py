from __future__ import annotations

from typing import Any

from app.hub.paper_executor import PaperExecutor
from app.hub.pipeline import evaluate_scan


class TradingHubRunner:
    """Orchestrates scan -> decision -> paper execution without live orders."""

    def __init__(self, scanner, executor: PaperExecutor | None = None):
        self.scanner = scanner
        self.executor = executor or PaperExecutor()

    def evaluate(self, symbol: str) -> dict[str, Any]:
        scan = self.scanner.scan(symbol)
        decision = evaluate_scan(scan)
        price = self._latest_price(scan)
        execution = self.executor.execute(decision, price) if price is not None else {"status": "SKIPPED", "reason": "no price"}
        return {"scan": scan, "decision": decision, "execution": execution}

    @staticmethod
    def _latest_price(scan: dict[str, Any]) -> float | None:
        frames = scan.get("timeframes", {})
        if not frames:
            return None
        frame = frames.get("5m") or next(iter(frames.values()))
        candles = frame.get("market", {}).get("candles", [])
        return float(candles[-1]["close"]) if candles else None
