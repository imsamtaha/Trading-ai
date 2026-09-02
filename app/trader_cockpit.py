"""Trader Cockpit state helpers.

This module keeps the UI-facing model deliberately small: account, P/L,
positions, ATLAS state, risk state, and broker connection state.
"""
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class AtlasState:
    decision: str = "WAIT"
    strength: str = "Monitoring"
    alignment: str = "No active alignment"
    aligned_timeframes: int = 0
    total_timeframes: int = 4


@dataclass(frozen=True)
class RiskState:
    level: str = "LOW"
    daily_risk_percent: float = 0.0
    max_daily_loss_percent: float = 2.0


def build_cockpit_state(
    account: dict[str, Any],
    equity: dict[str, Any],
    positions: list[dict[str, Any]],
    prices: dict[str, float],
    atlas: AtlasState | None = None,
    risk: RiskState | None = None,
    broker: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a stable payload for the Trader Cockpit frontend."""
    atlas = atlas or AtlasState()
    risk = risk or RiskState()
    broker = broker or {
        "provider": None,
        "account_id": None,
        "environment": "paper",
        "status": "connected",
    }

    return {
        "status": "LIVE",
        "mode": "paper_trading",
        "account": account,
        "equity": equity,
        "prices": prices,
        "positions": positions,
        "atlas": asdict(atlas),
        "risk": asdict(risk),
        "broker": broker,
    }
