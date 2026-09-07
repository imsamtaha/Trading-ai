import os
from dataclasses import dataclass
from typing import Any, Callable

from app.analysis.structure import analyze_structure
from app.analysis.technical import analyze_candles
from app.data.market import get_candles
from app.paper_trading.engine import PersistentPaperTradingEngine
from app.risk.manager import calculate_risk
from app.strategies.signal import generate_signal
from app.strategies.trade import create_trade_candidate


@dataclass(frozen=True)
class AgentTool:
    name: str
    description: str
    risk: str
    execute: Callable[..., Any]


def market_analysis(symbol: str, interval: str = "1h", limit: int = 100, account_balance: float = 10000.0) -> dict:
    market_data = get_candles(symbol.upper(), interval, limit)
    candles = market_data["candles"]
    technical = analyze_candles(candles)
    structure = analyze_structure(candles)
    signal = generate_signal(technical, structure)
    trade = create_trade_candidate(signal, technical, account_balance=account_balance)
    return {
        "symbol": market_data["symbol"],
        "interval": market_data["interval"],
        "candles": market_data["count"],
        "technical": technical,
        "structure": structure,
        "signal": signal,
        "trade": trade,
    }


def risk_evaluate(trade: dict, account_balance: float = 10000.0, risk_percent: float = 1.0) -> dict:
    if trade.get("status") != "TRADE_CANDIDATE":
        return {"approved": False, "reason": "No actionable trade candidate."}

    return calculate_risk(
        direction=trade["direction"],
        entry=float(trade["entry"]),
        stop_loss=float(trade["stop_loss"]),
        take_profit=float(trade["take_profit"]),
        account_balance=account_balance,
        risk_percent=risk_percent,
    )


def paper_positions(account_id: int) -> list[dict]:
    return PersistentPaperTradingEngine(account_id).positions()


def paper_execute(account_id: int, symbol: str, trade: dict, *, confirmed: bool = False) -> dict:
    if os.getenv("ATLAS_AGENT_PAPER_EXECUTION_ENABLED", "false").lower() != "true":
        raise PermissionError("ATLAS agent paper execution is disabled.")
    if not confirmed:
        raise PermissionError("Explicit paper execution confirmation is required.")
    if trade.get("status") != "TRADE_CANDIDATE":
        raise ValueError("Only validated trade candidates can be paper executed.")

    risk = trade.get("risk") or {}
    if not risk.get("approved"):
        raise ValueError("Risk engine did not approve this trade candidate.")

    engine = PersistentPaperTradingEngine(account_id)
    return engine.open_position(
        symbol=symbol.upper(),
        direction=trade["direction"],
        entry=float(trade["entry"]),
        stop_loss=float(trade["stop_loss"]),
        take_profit=float(trade["take_profit"]),
        position_size=float(risk["position_size"]),
    )


TOOLS = {
    "market.analyze": AgentTool(
        "market.analyze",
        "Run ATLAS market, technical, structure, signal and trade-candidate analysis.",
        "read",
        market_analysis,
    ),
    "risk.evaluate": AgentTool(
        "risk.evaluate",
        "Re-evaluate a trade candidate through the deterministic ATLAS risk engine.",
        "read",
        risk_evaluate,
    ),
    "paper.positions": AgentTool(
        "paper.positions",
        "Read positions from an ATLAS paper account.",
        "read",
        paper_positions,
    ),
    "paper.execute": AgentTool(
        "paper.execute",
        "Open a simulated paper position after explicit confirmation and risk approval.",
        "paper-write",
        paper_execute,
    ),
}
