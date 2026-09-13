from datetime import datetime, timezone

class RiskScoreEngine:
    POLICY_VERSION = "atlas-risk-v1"

    def evaluate(
        self,
        *,
        risk_percent,
        daily_loss_percent,
        weekly_loss_percent,
        drawdown_percent,
        open_positions,
        same_symbol_positions,
        spread_ok,
        data_fresh,
        stop_loss_valid,
    ):
        assessed_at = datetime.now(timezone.utc).isoformat()

        if not stop_loss_valid:
            return {
                "risk_score": 100,
                "risk_level": "HARD_BLOCK",
                "action": "BLOCK",
                "reasons": ["INVALID_STOP_LOSS"],
                "policy_version": self.POLICY_VERSION,
            "assessed_at": assessed_at,
                "assessed_at": assessed_at,
            }

        if not data_fresh:
            return {
                "risk_score": 80,
                "risk_level": "HARD_BLOCK",
                "action": "BLOCK",
                "reasons": ["STALE_DATA"],
                "policy_version": self.POLICY_VERSION,
            "assessed_at": assessed_at,
                "assessed_at": assessed_at,
            }

        if not spread_ok:
            return {
                "risk_score": 80,
                "risk_level": "HARD_BLOCK",
                "action": "BLOCK",
                "reasons": ["EXCESSIVE_SPREAD"],
                "policy_version": self.POLICY_VERSION,
            "assessed_at": assessed_at,
                "assessed_at": assessed_at,
            }

        if (
            daily_loss_percent is None
            or weekly_loss_percent is None
            or drawdown_percent is None
            or open_positions is None
            or same_symbol_positions is None
        ):
            return {
                "risk_score": 100,
                "risk_level": "HARD_BLOCK",
                "action": "BLOCK",
                "reasons": ["MISSING_RISK_DATA"],
                "policy_version": self.POLICY_VERSION,
            "assessed_at": assessed_at,
                "assessed_at": assessed_at,
            }

        if (
            daily_loss_percent >= 2.0
            or weekly_loss_percent >= 4.0
            or drawdown_percent >= 6.0
            or open_positions >= 3
            or same_symbol_positions >= 1
        ):
            return {
                "risk_score": 70,
                "risk_level": "BLOCK",
                "action": "BLOCK",
                "reasons": [
                    "DAILY_LOSS_LIMIT"
                    if daily_loss_percent >= 2.0
                    else "WEEKLY_LOSS_LIMIT"
                    if weekly_loss_percent >= 4.0
                    else "MAX_DRAWDOWN"
                    if drawdown_percent >= 6.0
                    else "MAX_OPEN_POSITIONS"
                    if open_positions >= 3
                    else "SAME_SYMBOL_POSITION_LIMIT"
                ],
                "policy_version": self.POLICY_VERSION,
            "assessed_at": assessed_at,
                "assessed_at": assessed_at,
            }

        if risk_percent > 0.50:
            return {
                "risk_score": 40,
                "risk_level": "REDUCED_RISK",
                "action": "REDUCE",
                "reasons": ["PER_TRADE_POLICY_EXCEEDED"],
                "policy_version": self.POLICY_VERSION,
            "assessed_at": assessed_at,
                "assessed_at": assessed_at,
            }

        return {
            "risk_score": 20,
            "risk_level": "ELIGIBLE",
            "action": "ALLOW_DEMO",
            "policy_version": self.POLICY_VERSION,
            "assessed_at": assessed_at,
        }

