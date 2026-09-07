from app.agent.models import AgentDecision, AgentRequest
from app.agent.tools import market_analysis, risk_evaluate


class AtlasAgent:
    """Paper-only decision orchestrator for ATLAS.

    The deterministic trading engines remain authoritative. The agent combines
    their outputs, selects specialist skills, and explains the resulting state.
    It never routes orders to MT5.
    """

    def assess(self, request: AgentRequest) -> AgentDecision:
        analysis = market_analysis(
            symbol=request.symbol,
            interval=request.interval,
            limit=request.limit,
            account_balance=request.account_balance,
        )

        technical = analysis["technical"]
        structure = analysis["structure"]
        signal = analysis["signal"]
        trade = analysis["trade"]

        selected_skills = [
            "market-analysis",
            "technical-analysis",
            "market-structure",
        ]

        rationale: list[str] = []
        trend = technical.get("trend", "unknown")
        momentum = technical.get("momentum", "unknown")
        direction = str(signal.get("direction") or "WAIT").upper()
        confidence = float(signal.get("confidence") or 0.0)

        rationale.append(f"Technical trend: {trend}.")
        rationale.append(f"Momentum state: {momentum}.")
        rationale.append(f"Signal engine direction: {direction} at {confidence:.1f}% confidence.")

        risk = {"approved": False, "reason": "No actionable trade candidate."}
        status = str(trade.get("status") or "NO_TRADE")
        final_decision = "WAIT"

        if status == "TRADE_CANDIDATE":
            selected_skills.append("risk-management")
            risk = risk_evaluate(
                trade,
                account_balance=request.account_balance,
                risk_percent=request.risk_percent,
            )
            if risk.get("approved"):
                final_decision = "PAPER_CANDIDATE"
                rationale.append(
                    f"Risk engine approved the setup at R:R {risk.get('risk_reward')}."
                )
            else:
                status = "REJECTED"
                rationale.append(f"Risk engine rejected the setup: {risk.get('reason')}")
        else:
            rationale.append(str(trade.get("reason") or "No actionable setup."))

        return AgentDecision(
            symbol=analysis["symbol"],
            interval=analysis["interval"],
            decision=final_decision,
            confidence=confidence,
            status=status,
            rationale=rationale,
            technical=technical,
            structure=structure,
            signal=signal,
            trade=trade,
            risk=risk,
            selected_skills=selected_skills,
            paper_only=True,
        )
