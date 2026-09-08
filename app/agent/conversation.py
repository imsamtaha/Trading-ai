from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from app.agent.core import AtlasAgent
from app.agent.models import AgentRequest
from app.agent.right_hand import build_right_hand_plan


SUPPORTED_MARKET_SYMBOLS = {
    "GOLD": "XAUUSD",
    "XAU": "XAUUSD",
    "XAUUSD": "XAUUSD",
    "SILVER": "XAGUSD",
    "XAG": "XAGUSD",
    "XAGUSD": "XAGUSD",
    "GAS": "GAS",
    "EURUSD": "EURUSD",
    "XRP": "XRPUSDT",
    "XRPUSDT": "XRPUSDT",
    "SOL": "SOLUSDT",
    "SOLUSDT": "SOLUSDT",
}


@dataclass
class ConversationResult:
    request: str
    specialist: str
    specialist_name: str
    status: str
    message: str
    selected_skills: list[str] = field(default_factory=list)
    suggested_tools: list[str] = field(default_factory=list)
    approval_required: bool = False
    execution_mode: str = "assist"
    result: dict[str, Any] = field(default_factory=dict)
    constraints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _extract_market_symbol(text: str) -> str | None:
    tokens = re.findall(r"[A-Z0-9.]+", text.upper())
    for token in tokens:
        symbol = SUPPORTED_MARKET_SYMBOLS.get(token)
        if symbol:
            return symbol
    return None


def converse(
    text: str,
    *,
    interval: str = "15m",
    multi_timeframe: bool = True,
    account_balance: float = 10000.0,
    risk_percent: float = 1.0,
) -> ConversationResult:
    plan = build_right_hand_plan(text)

    if plan.primary_specialist != "market":
        return ConversationResult(
            request=plan.request,
            specialist=plan.primary_specialist,
            specialist_name=plan.specialist_name,
            status="PLANNED",
            message=(
                f"Routed to {plan.specialist_name}. This ATLAS server can plan the task, "
                "but it will not claim external tools ran unless a verified connector is wired for that action."
            ),
            selected_skills=plan.selected_skills,
            suggested_tools=plan.suggested_tools,
            approval_required=plan.approval_required,
            execution_mode=plan.execution_mode,
            result={"steps": plan.steps},
            constraints=plan.constraints,
        )

    symbol = _extract_market_symbol(text)
    if not symbol:
        return ConversationResult(
            request=plan.request,
            specialist=plan.primary_specialist,
            specialist_name=plan.specialist_name,
            status="NEEDS_CONTEXT",
            message="Market request detected, but no supported symbol was found in the request.",
            selected_skills=plan.selected_skills,
            suggested_tools=plan.suggested_tools,
            approval_required=True,
            execution_mode="paper_only",
            result={"supported_symbols": sorted(set(SUPPORTED_MARKET_SYMBOLS.values()))},
            constraints=plan.constraints,
        )

    request = AgentRequest(
        symbol=symbol,
        interval=interval,
        limit=120,
        account_balance=account_balance,
        risk_percent=risk_percent,
    )
    agent = AtlasAgent()
    decision = agent.assess_multi_timeframe(request) if multi_timeframe else agent.assess(request)

    return ConversationResult(
        request=plan.request,
        specialist=plan.primary_specialist,
        specialist_name=plan.specialist_name,
        status="COMPLETED",
        message=(
            f"Paper-only market analysis completed for {symbol}. "
            f"Decision: {decision.decision}; confidence: {decision.confidence:.1f}%."
        ),
        selected_skills=decision.selected_skills,
        suggested_tools=plan.suggested_tools,
        approval_required=True,
        execution_mode="paper_only",
        result=decision.to_dict(),
        constraints=plan.constraints,
    )
