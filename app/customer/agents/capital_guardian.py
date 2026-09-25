from dataclasses import dataclass

from app.customer.contracts import MarketSnapshot


@dataclass(frozen=True)
class CapitalDecision:
    approved: bool
    blockers: tuple[str, ...]
    requested_risk_pct: float


def evaluate_capital(
    snapshot: MarketSnapshot,
    *,
    requested_risk_pct: float,
    max_drawdown_pct: float = 3.0,
    max_total_open_risk_pct: float = 3.0,
) -> CapitalDecision:
    blockers = []
    equity = float(snapshot.account.get("equity", 0.0) or 0.0)
    drawdown = float(snapshot.account.get("drawdown_pct", 0.0) or 0.0)
    open_risk = float(snapshot.account.get("open_risk_pct", 0.0) or 0.0)
    if equity <= 0:
        blockers.append("account equity is invalid")
    if drawdown >= max_drawdown_pct:
        blockers.append("drawdown limit reached")
    if requested_risk_pct <= 0 or open_risk + requested_risk_pct > max_total_open_risk_pct:
        blockers.append("aggregate open risk limit would be exceeded")
    return CapitalDecision(not blockers, tuple(blockers), requested_risk_pct)
