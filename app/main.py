from fastapi import FastAPI, HTTPException

from app.data.market import get_price, get_candles
from app.analysis.technical import analyze_candles
from app.analysis.structure import analyze_structure
from app.strategies.signal import generate_signal
from app.strategies.trade import create_trade_candidate
from app.ai.analyst import analyze_market

from app.database.repository import (
    get_account,
    get_trades,
)

from app.performance.metrics import calculate_metrics
from app.dashboard import router as dashboard_router


app = FastAPI(
    title="Trading AI",
    description="AI-powered market analysis and paper-trading platform",
    version="0.8.0",
)

app.include_router(dashboard_router)


@app.get("/")
def root():
    return {
        "system": "Trading AI",
        "status": "online",
        "mode": "paper_trading",
        "version": "0.8.0",
        "dashboard": "/dashboard",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "trading-ai-api",
    }


@app.get("/market/{symbol}")
def market(symbol: str):
    try:
        return get_price(symbol.upper())

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        )


@app.get("/market/{symbol}/candles")
def candles(
    symbol: str,
    interval: str = "1h",
    limit: int = 100,
):
    try:
        return get_candles(
            symbol.upper(),
            interval,
            limit,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        )


@app.get("/analysis/{symbol}")
def analysis(
    symbol: str,
    interval: str = "1h",
    limit: int = 100,
):
    try:
        market_data = get_candles(
            symbol.upper(),
            interval,
            limit,
        )

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


@app.get("/performance/{account_id}")
def performance(account_id: int):
    account = get_account(account_id)

    if not account:
        raise HTTPException(
            status_code=404,
            detail="Paper account not found.",
        )

    trades = get_trades(account_id)
    metrics = calculate_metrics(
        trades,
        initial_balance=account["initial_balance"],
    )

    return {
        "account_id": account_id,
        "account": account,
        "metrics": metrics,
        "trades": trades,
    }
