from pathlib import Path
from dotenv import load_dotenv

# Load Windows server configuration before constructing routers/services.
# Existing process environment variables retain precedence.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.data.market import get_price, get_candles
from app.analysis.technical import analyze_candles
from app.analysis.structure import analyze_structure
from app.strategies.signal import generate_signal
from app.strategies.trade import create_trade_candidate
from app.ai.analyst import analyze_market
from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError
from app.execution.atlas import AtlasExecutionService, ExecutionPolicy
from app.execution.mt5_state import MT5CockpitAdapter
from app.execution.provider_mode import mt5_connections_paused, ctrader_selected
from app.database.repository import get_account, get_trades
from app.performance.metrics import calculate_metrics
from app.dashboard import router as dashboard_router
from app.subscription import router as subscription_router
from app.billing import router as billing_router
from app.dashboard.preferences import router as preferences_router
from app.auth import router as auth_router


app = FastAPI(
    title="ATLAS Trading AI",
    description="Multi-asset AI trading analysis, decision support, and MT5 execution gateway",
    version="1.2.0",
)

app.include_router(dashboard_router)
app.include_router(subscription_router)
app.include_router(billing_router)
app.include_router(preferences_router)
app.include_router(auth_router)


@app.middleware("http")
async def dashboard_only_guard(request: Request, call_next):
    """Public-view safety mode.

    With ATLAS_DASHBOARD_ONLY=true, only the subscriber landing page, live
    read-only dashboard telemetry, health, and documentation routes are public.
    Execution/mutation endpoints remain blocked at the FastAPI origin.
    """
    import os

    path = request.url.path.rstrip("/") or "/"
    if mt5_connections_paused() and (
        path.startswith(("/mt5/", "/api/mt5-demo/"))
        or path in {
            "/dashboard/atlas", "/dashboard/mt5-state", "/subscription/mt5-request",
            "/api/runtime/demo-execution", "/api/runtime/learned-council",
            "/api/demo-executive/start", "/api/execution-guard/evaluate",
        }
        or path.startswith("/api/execution-guard/confirm/")
    ):
        return JSONResponse(
            status_code=503, content={"status": "PAUSED", "detail": "MT5 connections and setups are paused."},
            headers={"Cache-Control": "no-store"},
        )
    path = request.url.path
    if path in {"/dashboard/atlas", "/dashboard/mt5-state", "/mt5/cockpit-state"}:
        return JSONResponse(status_code=403, content={"detail": "Shared MT5 telemetry is disabled."})

    dashboard_only = os.getenv("ATLAS_DASHBOARD_ONLY", "false").lower() == "true"
    if dashboard_only:
        allowed = (
            path.startswith("/billing/")
            or path.startswith("/auth/")
            or path.startswith("/api/")
            or path in {
                "/",
                "/health",
                "/login",
                "/logout",
                "/dashboard",
                "/dashboard/market-briefing",
                "/app/dashboard",
                "/ui/preferences.js",
                "/subscribe",
                "/subscription/request",
                "/subscription/mt5-request",
                "/docs",
                "/openapi.json",
            }
        )
        if not allowed:
            return JSONResponse(status_code=403, content={"detail": "Dashboard-only mode is enabled."})
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


@app.get("/", response_class=HTMLResponse)
def root():
    return HTMLResponse("<!doctype html><html><body><main><h1>ATLAS</h1><p>Private trading intelligence workspace.</p><a href='/login'>Enter ATLAS</a></main></body></html>")


@app.get("/health")
async def health():
    # Liveness must not wait for the worker pool used by broker/provider reads.
    return {
        "status": "healthy", "service": "atlas-trading-api",
        "mt5_paused": mt5_connections_paused(),
        "broker_provider": "ctrader" if ctrader_selected() else None,
    }


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
):
    """Route an order only through the private ATLAS execution gate.

    The default is dry-run; dashboard-only mode blocks this endpoint.
    """
    service = _mt5_service()
    try:
        service.broker.connect()
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
