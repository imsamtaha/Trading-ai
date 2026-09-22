from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

try:
    import MetaTrader5 as mt5
except ImportError:  # pragma: no cover - Windows worker dependency
    mt5 = None

from fastapi import APIRouter, HTTPException

from app.dashboard.market_briefing import get_market_briefing
from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError
from app.intelligence.confidence import SignalQualityEngine
from app.integrations.supabase_journal import SupabaseJournalError, SupabaseSignalJournal
from app.integrations.mt5_bridge import RemoteMT5BridgeError, fetch_remote_mt5_telemetry
from app.dashboard.market_intelligence import MarketIntelligenceFeed
from app.strategy.universe import build_universe

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
_market_intelligence = MarketIntelligenceFeed()


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, "true" if default else "false").lower() == "true"


def _mask_login(login: object) -> str:
    token = str(login or "")
    return f"***{token[-4:]}" if token else "***"


def _account_type(raw_account: Any) -> str:
    # MT5: 0=demo, 1=contest, 2=real.
    return {0: "DEMO", 1: "CONTEST", 2: "REAL"}.get(
        int(getattr(raw_account, "trade_mode", -1)),
        "UNKNOWN",
    )


def _public_account(account: dict[str, Any], raw_account: Any) -> dict[str, Any]:
    show_balance = _env_bool("ATLAS_PUBLIC_SHOW_BALANCE", True)
    balance = float(account.get("balance", 0.0) or 0.0)
    equity = float(account.get("equity", 0.0) or 0.0)
    margin = float(getattr(raw_account, "margin", 0.0) or 0.0)
    margin_free = float(getattr(raw_account, "margin_free", 0.0) or 0.0)
    floating_profit = float(getattr(raw_account, "profit", equity - balance) or 0.0)
    margin_level = (equity / margin * 100.0) if margin > 0 else 0.0

    return {
        "label": os.getenv("ATLAS_PUBLIC_ACCOUNT_LABEL", "ATLAS VERIFIED ACCOUNT"),
        "login": _mask_login(account.get("login")),
        "account_type": _account_type(raw_account),
        "broker_company": str(getattr(raw_account, "company", "") or ""),
        "server": str(account.get("server", "")),
        "currency": str(account.get("currency", "")),
        "balance": round(balance, 2) if show_balance else None,
        "equity": round(equity, 2) if show_balance else None,
        "floating_profit": round(floating_profit, 2) if show_balance else None,
        "margin": round(margin, 2) if show_balance else None,
        "margin_free": round(margin_free, 2) if show_balance else None,
        "margin_level": round(margin_level, 2) if show_balance else None,
        "leverage": int(getattr(raw_account, "leverage", 0) or 0),
        "trade_allowed": bool(account.get("trade_allowed", False)),
    }


def _analysis_tools() -> tuple[dict[str, int], Any, Any]:
    """Load Windows-only MT5 analysis helpers only when the cockpit needs them."""
    try:
        from scripts.atlas_mt5_cycle import TIMEFRAMES, analyze_timeframe, build_decision
    except ImportError as exc:  # Linux dashboard tests have no MetaTrader5 package.
        raise MT5ExecutionError("MT5 analysis helpers are unavailable on this host.") from exc
    return TIMEFRAMES, analyze_timeframe, build_decision


def _monitor_symbol(
    broker: MT5Broker,
    symbol: str,
    canonical_symbol: str,
    asset_class: str,
    opportunity_score: float,
    count: int = 120,
) -> dict[str, Any]:
    quality_engine = SignalQualityEngine()
    timeframes, analyze_timeframe, build_decision = _analysis_tools()
    results = {
        tf: analyze_timeframe(broker, symbol, mt5_tf, count)
        for tf, mt5_tf in timeframes.items()
    }
    decision, _, _, _ = build_decision(results)
    quality = quality_engine.evaluate(decision, decision.get("mtf_alignment", "UNKNOWN"))
    quote = broker.quote(symbol)
    price = quote.get("last") or quote.get("bid") or quote.get("ask") or 0.0
    return {
        "symbol": symbol,
        "canonical_symbol": canonical_symbol,
        "asset_class": asset_class,
        "opportunity_score": opportunity_score,
        "price": float(price),
        "spread_points": round(float(quote.get("spread_points", 0.0) or 0.0), 2),
        "decision": decision,
        "quality": quality,
        "timeframes": {
            tf: {
                "trend": item["technical"].get("trend"),
                "momentum": item["technical"].get("momentum"),
                "macd": item["technical"].get("macd_signal"),
                "structure": item["structure"].get("structure"),
                "signal": item["signal"].get("direction"),
                "score": item["signal"].get("score"),
            }
            for tf, item in results.items()
        },
    }


@router.get("/markets")
def financial_market_state() -> dict[str, Any]:
    """Server-side Wall Street board and financial-news snapshot."""
    return _market_intelligence.snapshot()


@router.get("/market-briefing")
def market_briefing() -> dict[str, Any]:
    return get_market_briefing()


@router.get("/state")
@router.get("/atlas")
def atlas_dashboard_state() -> dict[str, Any]:
    if os.getenv("ATLAS_MT5_BRIDGE_URL", "").strip():
        try:
            return fetch_remote_mt5_telemetry()
        except RemoteMT5BridgeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    broker = MT5Broker(MT5Config.from_env())
    try:
        account = broker.connect()
        if mt5 is None:
            raise MT5ExecutionError("MetaTrader5 package unavailable on this host.")
        raw_account = mt5.account_info()
        if raw_account is None:
            raise MT5ExecutionError("MT5 account metadata unavailable.")

        top_n = max(1, min(30, int(os.getenv("ATLAS_DASHBOARD_TOP_N", "12"))))
        universe = build_universe(broker.symbols(), top_n=top_n)
        symbols: list[dict[str, Any]] = []
        symbol_errors: list[dict[str, str]] = []
        for item in universe:
            try:
                symbols.append(_monitor_symbol(
                    broker,
                    item.broker_symbol,
                    item.canonical_symbol,
                    item.asset_class,
                    item.opportunity_score,
                ))
            except Exception as exc:
                symbol_errors.append({"symbol": item.broker_symbol, "error": str(exc)})

        positions = broker.positions()
        public_positions = [
            {
                "symbol": p["symbol"],
                "direction": p["direction"],
                "volume": p["volume"],
                "price_open": p["price_open"],
                "sl": p["sl"],
                "tp": p["tp"],
                "profit": p["profit"],
            }
            for p in positions
        ] if _env_bool("ATLAS_PUBLIC_SHOW_POSITIONS", True) else []

        alerts = [
            {
                "symbol": item["symbol"],
                "type": "signal",
                "message": (
                    f"{item['decision']['decision']} · score {item['decision']['score']} · "
                    f"confidence {item['quality']['execution_confidence']}"
                ),
            }
            for item in symbols
            if item["decision"]["decision"] in {"BUY", "SELL", "NO_TRADE"}
        ]

        try:
            SupabaseSignalJournal()
            journal_status = "READY"
        except SupabaseJournalError:
            journal_status = "NOT_CONFIGURED"

        financial_market = _market_intelligence.snapshot()
        account_type = _account_type(raw_account)
        execution_enabled = (
            _env_bool("ATLAS_LIVE_TRADING", False)
            and account_type == "REAL"
            and bool(account.get("trade_allowed", False))
        )
        live_demo = (
            _env_bool("ATLAS_LIVE_DEMO", False)
            and account_type == "DEMO"
        )
        return {
            "status": "ONLINE",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": "LIVE_EXECUTION" if execution_enabled else ("LIVE_DEMO" if live_demo else "READ_ONLY"),
            "account": _public_account(account, raw_account),
            "verified_live_account": account_type == "REAL",
            "symbols": symbols,
            "positions": public_positions,
            "open_positions": len(positions),
            "floating_position_pnl": round(sum(float(p.get("profit", 0.0) or 0.0) for p in positions), 2),
            "alerts": alerts,
            "symbol_errors": symbol_errors,
            "financial_market": financial_market,
            "services": {
                "mt5": "ONLINE",
                "supabase": journal_status,
                "execution_gate": "ENABLED" if execution_enabled else ("DEMO_SIMULATED" if live_demo else "DISABLED"),
                "subscriber_access": "LIVE_DEMO" if live_demo else "READ_ONLY",
                "financial_markets": financial_market["status"],
            },
            "disclaimer": (
                "LIVE DEMO uses real-time MT5 demo data with simulated ATLAS execution. Real-money trading is off."
                if live_demo
                else "Account and strategy telemetry only. Past or current results do not guarantee future performance."
            ),
        }
    except MT5ExecutionError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    finally:
        broker.disconnect()
