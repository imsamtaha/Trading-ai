from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.dashboard.api import router as api_router
from app.dashboard.agent_panel import router as agent_panel_router
from app.dashboard.views import DASHBOARD_HTML

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse, tags=["dashboard"])
def dashboard_view() -> HTMLResponse:
    scripts = (
        '<script src="/ui/preferences.js"></script>'
        '<script src="/ui/agent-panel.js"></script>'
    )
    return HTMLResponse(DASHBOARD_HTML.replace("</body>", scripts + "</body>"))


router.include_router(api_router)
router.include_router(agent_panel_router)

__all__ = ["router"]

# Compatibility API for the read-only analysis demo. No orders or ledger writes.
ATLAS_DEMO_SYMBOLS = ["XAUUSD", "GAS", "XAGUSD", "EURUSD", "XRPUSDT", "SOLUSDT"]


def _demo_regime_from_technical(technical):
    from app.intelligence.regime.engine import MarketRegimeEngine, MarketState

    direction = {"bullish": 0.8, "bearish": -0.8}
    price = float(technical.get("price") or 0)
    atr = float((technical.get("indicators") or {}).get("atr_14") or 0)
    state = MarketState(
        trend_score=direction.get(str(technical.get("trend", "")).lower(), 0.0),
        momentum_score=direction.get(str(technical.get("momentum", "")).lower(), 0.0),
        volatility_score=min(1.0, max(0.0, atr / price * 10)) if price > 0 else 0.0,
        volume_score={"high": 0.8, "normal": 0.0, "low": -0.5}.get(
            str(technical.get("volume_state", "")).lower(), 0.0),
        event_risk_score=0.0,
        risk_sentiment_score=0.0,
    )
    result = MarketRegimeEngine().analyze(state)
    result["context_limitations"] = ["News and risk sentiment are not evaluated."]
    return result


def _analyze_demo_symbol(symbol, interval, account_balance):
    from app.data.market import get_candles
    from app.analysis.technical import analyze_candles
    from app.analysis.structure import analyze_structure
    from app.strategies.signal import generate_signal
    from app.strategies.trade import create_trade_candidate

    market = get_candles(symbol, interval, 120)
    technical = analyze_candles(market["candles"])
    structure = analyze_structure(market["candles"])
    signal = generate_signal(technical, structure)
    candidate = create_trade_candidate(signal, technical, account_balance)
    return {
        "symbol": symbol, "interval": interval,
        "status": candidate["status"],
        "technical": technical, "structure": structure,
        "regime": _demo_regime_from_technical(technical),
        "signal": signal, "trade_candidate": candidate,
        "execution": "disabled",
        "data_source": "Public market provider; commodity prices may be futures proxies.",
    }


def atlas_demo_state(interval="15m", account_balance=10000.0):
    import math

    if interval not in {"5m", "15m", "30m", "1h"}:
        raise ValueError("Unsupported demo interval")
    if not math.isfinite(account_balance) or account_balance <= 0:
        raise ValueError("Account balance must be positive and finite")
    results = []
    for symbol in ATLAS_DEMO_SYMBOLS:
        try:
            results.append(_analyze_demo_symbol(symbol, interval, account_balance))
        except Exception:
            results.append({"symbol": symbol, "interval": interval,
                            "status": "ERROR", "error": "Market analysis unavailable"})
    errors = sum(item["status"] == "ERROR" for item in results)
    return {
        "status": "DEMO_READY" if errors < len(results) else "DEMO_UNAVAILABLE",
        "execution": "disabled",
        "results": results,
        "summary": {
            "analyzed": len(results),
            "no_trades": sum(item["status"] == "NO_TRADE" for item in results),
            "errors": errors,
        },
        "disclaimer": "Read-only analysis, not executed demo trades or verified performance.",
    }
