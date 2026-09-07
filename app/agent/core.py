from dataclasses import replace
from math import isfinite

from app.agent.models import AgentDecision, AgentRequest, MULTI_TIMEFRAMES
from app.agent.tools import market_analysis, risk_evaluate


class AtlasAgent:
    """Paper-only decision orchestrator for ATLAS.

    The deterministic trading engines remain authoritative. The agent combines
    their outputs, selects specialist skills, and explains the resulting state.
    It never routes orders to MT5.
    """

    def assess_multi_timeframe(self, request: AgentRequest) -> AgentDecision:
        """Require unanimous actionable signals and risk approval on all frames.

        The 5m engine candidate supplies the unmodified entry/stop/target.
        Failed frames veto the aggregate; successful frames remain inspectable.
        """
        frames = {}
        blockers = []
        for interval in MULTI_TIMEFRAMES:
            try:
                result = self.assess(replace(request, interval=interval))
                if result.symbol != request.symbol.upper() or result.interval != interval:
                    raise ValueError("Analysis identity mismatch")
                if not isfinite(result.confidence) or not 0 <= result.confidence <= 100:
                    raise ValueError("Invalid signal confidence")
                frames[interval] = result
                direction = result.signal.get("direction")
                if (result.decision != "PAPER_CANDIDATE"
                        or result.risk.get("approved") is not True
                        or direction not in {"LONG", "SHORT"}
                        or result.trade.get("direction") != direction):
                    blockers.append(f"{interval}: signal/candidate/risk did not approve an actionable setup.")
            except Exception:
                frames[interval] = AgentDecision(
                    symbol=request.symbol.upper(), interval=interval,
                    decision="WAIT", confidence=0.0, status="UNAVAILABLE",
                    rationale=["Analysis unavailable or invalid; retry when data is available."],
                    risk={"approved": False, "reason": "Analysis unavailable or invalid."},
                )
                blockers.append(f"{interval}: analysis unavailable or invalid.")

        directions = {frame.signal.get("direction") for frame in frames.values()}
        if len(directions) != 1 or not directions.issubset({"LONG", "SHORT"}):
            blockers.append("All four signal engines must agree on LONG or SHORT.")
        approved = not blockers
        anchor = frames["5m"]
        rationale = blockers or [
            "All four signal engines agree and all four risk evaluations approved.",
            "Candidate levels come unchanged from the 5m engine; confidence is the lowest across frames.",
        ]
        risk = dict(anchor.risk) if approved else {"approved": False, "reason": " ".join(blockers)}
        trade = dict(anchor.trade, risk=risk) if approved else {"status": "NO_TRADE", "reason": " ".join(blockers)}
        return AgentDecision(
            symbol=request.symbol.upper(), interval="multi",
            decision="PAPER_CANDIDATE" if approved else "WAIT",
            confidence=min(frame.confidence for frame in frames.values()) if approved else 0.0,
            status="TRADE_CANDIDATE" if approved else "NO_TRADE",
            rationale=rationale, technical=anchor.technical, structure=anchor.structure,
            signal=dict(anchor.signal) if approved else {"direction": "WAIT", "confidence": 0.0},
            trade=trade, risk=risk,
            selected_skills=list(dict.fromkeys(skill for frame in frames.values() for skill in frame.selected_skills)),
            timeframe_decisions={interval: frame.to_dict() for interval, frame in frames.items()},
            candidate_interval="5m" if approved else None,
        )

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
