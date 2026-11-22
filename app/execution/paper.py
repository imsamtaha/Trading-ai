from __future__ import annotations

from typing import Any


class PaperBroker:
    """Owner-only non-broker execution adapter used for private strategy validation."""

    def market_order(
        self,
        *,
        symbol: str,
        direction: str,
        volume: float,
        stop_loss: float,
        take_profit: float,
        comment: str = "ATLAS-PAPER",
    ) -> dict[str, Any]:
        return {
            "status": "PAPER",
            "symbol": symbol,
            "side": direction.upper(),
            "volume": float(volume),
            "sl": float(stop_loss),
            "tp": float(take_profit),
            "comment": comment,
        }
