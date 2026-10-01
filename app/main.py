from pathlib import Path
from types import SimpleNamespace
from dotenv import load_dotenv

# Load Windows server configuration before constructing routers/services.
# Existing process environment variables retain precedence.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from app.website import router as website_router

from app.data.market import get_price, get_candles
from app.analysis.technical import analyze_candles
from app.analysis.structure import analyze_structure
from app.strategies.signal import generate_signal
from app.strategies.trade import create_trade_candidate
from app.ai.analyst import analyze_market
from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError
from app.execution.atlas import AtlasExecutionService, ExecutionPolicy
from app.execution.live_gate import LiveAuthorizationError, authorize_live_order
from app.execution.mt5_state import MT5CockpitAdapter
from app.database.repository import get_account, get_trades
from app.performance.metrics import calculate_metrics
from app.dashboard import router as dashboard_router
from app.subscription import router as subscription_router
from app.billing import router as billing_router
from app.dashboard.preferences import router as preferences_router
from app.agent.api import router as agent_router
from app.evolution.api import router as evolution_router


app = FastAPI(
    title="ATLAS ULTIMATE",
    description="Unified multi-asset AI trading intelligence, decision support, and MT5 gateway",
    version="1.8.0",
)

app.include_router(dashboard_router)
app.include_router(subscription_router)
app.include_router(billing_router)
app.include_router(preferences_router)
app.include_router(agent_router)
app.include_router(evolution_router)
app.include_router(website_router)


@app.middleware("http")
async def dashboard_only_guard(request: Request, call_next):
    """Allow the unified ATLAS UI, public reads and analysis-only POSTs; block execution and billing writes."""
    import os

    if os.getenv("ATLAS_DASHBOARD_ONLY", "false").lower() == "true":
        path = request.url.path
        read_paths = {
            "/", "/atlas-ultimate", "/health", "/api", "/subscribe", "/connect/fxpro", "/connect/fxpro-mt5", "/connect/fxpro-mt5/status",
            "/ui/preferences.js", "/ui/agent-panel.js", "/ui/demo-panel.js", "/ui/setups-panel.js",
            "/dashboard", "/dashboard/", "/dashboard/state", "/dashboard/atlas",
            "/dashboard/demo-status", "/dashboard/trader-view", "/dashboard/mt5-state", "/dashboard/active-setups",
            "/dashboard/market-briefing", "/dashboard/markets", "/mt5/cockpit-state",
            "/agent/capabilities", "/agent/right-hand/capabilities", "/agent/right-hand/tools",
            "/billing/methods", "/billing/plans", "/billing/whish/watch", "/billing/whish/reader", "/billing/whish/pro",
            "/evolution/status",
            "/docs", "/openapi.json",
        }
        analysis_paths = {"/agent/decision", "/agent/right-hand/plan", "/agent/right-hand/chat"}
        fxpro_demo_verify = request.method == "POST" and path == "/connect/fxpro-mt5/verify"
        paper_demo_execute = (
            request.method == "POST"
            and path == "/agent/paper/execute"
            and os.getenv("ATLAS_LIVE_DEMO", "false").lower() == "true"
            and os.getenv("ATLAS_AGENT_PAPER_EXECUTION_ENABLED", "false").lower() == "true"
        )
        whish_request = (
            request.method == "POST"
            and path.startswith("/billing/whish/")
            and path.endswith("/request")
            and os.getenv("ATLAS_WHISH_ENABLED", "false").lower() == "true"
        )
        public_analysis_enabled = (
            os.getenv("ATLAS_PUBLIC_ANALYSIS_ENABLED", "true").lower() == "true"
        )
        allowed = (
            request.method in {"GET", "HEAD"}
            and (path in read_paths or path.startswith("/assets/"))
        ) or whish_request or fxpro_demo_verify or paper_demo_execute or (
            public_analysis_enabled
            and request.method == "POST"
            and path in analysis_paths
        )
        if not allowed:
            return JSONResponse(
                status_code=403,
                content={"detail": "Dashboard-only mode is enabled."},
            )
    return await call_next(request)


def _mt5_service() -> AtlasExecutionService:
    config = MT5Config.from_env()
    policy = ExecutionPolicy(
        enabled=not config.dry_run,
        min_confidence=55.0,
        max_risk_level="MEDIUM",
        allow_buy=True,
        allow_sell=True,
    )
    return AtlasExecutionService(broker=MT5Broker(config), policy=policy)


def _redact_cockpit_state(state: dict) -> dict:
    account_id = str(state.get("account", {}).get("id", ""))
    masked = f"***{account_id[-4:]}" if account_id else "***"
    state["account"]["id"] = masked
    state["broker"]["account_id"] = masked
    return state


@app.get("/api")
def root():
    import os
    mode = "live_demo" if os.getenv("ATLAS_LIVE_DEMO", "false").lower() == "true" else "live_gateway_disabled_by_default"
    return {
        "system": "ATLAS ULTIMATE",
        "status": "online",
        "mode": mode,
        "version": "1.8.0",
        "main_ui": "/",
        "mt5_cockpit": "/mt5/cockpit-state",
        "market_briefing": "/dashboard/market-briefing",
        "agent": "/agent/capabilities",
        "right_hand": "/agent/right-hand/capabilities",
        "right_hand_chat": "/agent/right-hand/chat",
        "right_hand_tools": "/agent/right-hand/tools",
        "evolution": "/evolution/status",
    }


@app.get("/health")
def health():
    return {"status": "healthy", "service": "atlas-ultimate-api"}


@app.get("/market/{symbol}")
def market(symbol: str):
    try:
        return get_price(symbol.upper())
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/market/{symbol}/candles")
def candles(symbol: str, interval: str = "1h", limit: int = 100):
    try:
        return get_candles(symbol.upper(), interval, limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/analysis/{symbol}")
def analysis(symbol: str, interval: str = "1h", limit: int = 100):
    try:
        market_data = get_candles(symbol.upper(), interval, limit)
        candles_data = market_data["candles"]
        technical = analyze_candles(candles_data)
        structure = analyze_structure(candles_data)
        signal = generate_signal(technical, structure)
        trade = create_trade_candidate(signal, technical)
        ai_analysis = analyze_market(
            symbol=market_data["symbol"],
            interval=market_data["interval"],
            technical=technical,
            structure=structure,
            signal=signal,
            trade=trade,
        )
        return {
            "symbol": market_data["symbol"],
            "interval": market_data["interval"],
            "candles": market_data["count"],
            "technical": technical,
            "structure": structure,
            "signal": signal,
            "trade": trade,
            "ai_analysis": ai_analysis,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/mt5/status")
def mt5_status():
    broker = MT5Broker(MT5Config.from_env())
    try:
        account = broker.connect()
        return {
            "status": "connected",
            "account": account,
            "execution": _mt5_service().status(),
        }
    except MT5ExecutionError as exc:
        return {
            "status": "offline",
            "error": str(exc),
            "execution": _mt5_service().status(),
        }
    finally:
        broker.disconnect()


@app.get("/mt5/cockpit-state")
def mt5_cockpit_state():
    adapter = MT5CockpitAdapter()
    try:
        state = adapter.snapshot()
        return _redact_cockpit_state(state)
    except MT5ExecutionError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    finally:
        adapter.broker.disconnect()


@app.get("/mt5/positions")
def mt5_positions():
    broker = MT5Broker(MT5Config.from_env())
    try:
        broker.connect()
        return {"positions": broker.positions()}
    except MT5ExecutionError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    finally:
        broker.disconnect()


@app.get("/mt5/quote/{symbol}")
def mt5_quote(symbol: str):
    broker = MT5Broker(MT5Config.from_env())
    try:
        broker.connect()
        return broker.quote(symbol.upper())
    except MT5ExecutionError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    finally:
        broker.disconnect()


@app.post("/mt5/test-order")
def mt5_test_order(
    symbol: str,
    direction: str,
    volume: float,
    stop_loss: float,
    take_profit: float,
    confirmed: bool = False,
    authorization: str | None = Header(default=None),
):
    """Owner-confirmed real-account order through the private execution gate."""
    service = _mt5_service()
    if service.broker.config.dry_run:
        raise HTTPException(status_code=403, detail="Live execution is disabled.")
    try:
        account = service.broker.connect()
        authorize_live_order(
            authorization=authorization,
            confirmed=confirmed,
            account=SimpleNamespace(**{
                "login": account["login"],
                "trade_mode": account["trade_mode"],
                "trade_allowed": account["trade_allowed"],
            }),
        )
        decision = {
            "decision": direction.upper(),
            "confidence": 100.0,
            "risk_level": "LOW",
        }
        return service.execute(
            symbol=symbol.upper(),
            decision=decision,
            volume=volume,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
    except LiveAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except MT5ExecutionError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    finally:
        service.broker.disconnect()


@app.get("/performance/{account_id}")
def performance(account_id: int):
    account = get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Paper account not found.")
    trades = get_trades(account_id)
    metrics = calculate_metrics(trades, initial_balance=account["initial_balance"])
    return {
        "account_id": account_id,
        "account": account,
        "metrics": metrics,
        "trades": trades,
    }
