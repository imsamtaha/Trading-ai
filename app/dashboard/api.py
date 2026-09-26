from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

try:
    import MetaTrader5 as mt5
except ImportError:  # pragma: no cover - Windows worker dependency
    mt5 = None

from fastapi import APIRouter, HTTPException

from app.dashboard.market_briefing import get_market_briefing
from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError, account_type_name
from app.intelligence.confidence import SignalQualityEngine
from app.risk.engine import RiskScoreEngine
from app.integrations.supabase_journal import SupabaseJournalError, SupabaseSignalJournal
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
    return account_type_name(raw_account)


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
        "badge": f"{_account_type(raw_account)} · {str(account.get('server', ''))} · {_mask_login(account.get('login'))}",
    }



def _pending_orders() -> list[dict[str, Any]]:
    raw_orders = mt5.orders_get() if mt5 is not None else None
    items: list[dict[str, Any]] = []
    for order in raw_orders or ():
        order_type = int(getattr(order, "type", -1))
        direction = "BUY" if order_type == int(getattr(mt5, "ORDER_TYPE_BUY", 0)) else "SELL"
        items.append({
            "ticket": int(getattr(order, "ticket", 0) or 0),
            "symbol": str(getattr(order, "symbol", "") or ""),
            "direction": direction,
            "volume": float(getattr(order, "volume_initial", 0.0) or 0.0),
            "price_open": float(getattr(order, "price_open", 0.0) or 0.0),
            "sl": float(getattr(order, "sl", 0.0) or 0.0),
            "tp": float(getattr(order, "tp", 0.0) or 0.0),
            "time": int(getattr(order, "time_setup", 0) or 0),
        })
    return items


def _recent_trade_history(days: int = 7) -> list[dict[str, Any]]:
    if mt5 is None:
        return []
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=max(1, days))
    raw_deals = mt5.history_deals_get(start, end) or ()
    items: list[dict[str, Any]] = []
    for deal in raw_deals:
        entry = int(getattr(deal, "entry", -1))
        if entry != int(getattr(mt5, "DEAL_ENTRY_OUT", 1)):
            continue
        deal_type = int(getattr(deal, "type", -1))
        direction = "BUY" if deal_type == int(getattr(mt5, "DEAL_TYPE_BUY", 0)) else "SELL"
        items.append({
            "ticket": int(getattr(deal, "ticket", 0) or 0),
            "position_id": int(getattr(deal, "position_id", 0) or 0),
            "symbol": str(getattr(deal, "symbol", "") or ""),
            "direction": direction,
            "volume": float(getattr(deal, "volume", 0.0) or 0.0),
            "price": float(getattr(deal, "price", 0.0) or 0.0),
            "profit": float(getattr(deal, "profit", 0.0) or 0.0),
            "time": int(getattr(deal, "time", 0) or 0),
        })
    return sorted(items, key=lambda item: item["time"], reverse=True)[:50]

def _analysis_tools() -> tuple[dict[str, int], Any, Any]:
    """Load Windows-only MT5 analysis helpers only when the cockpit needs them."""
    try:
        from scripts.atlas_mt5_cycle import TIMEFRAMES, analyze_timeframe, build_decision
    except ImportError as exc:  # Linux dashboard tests have no MetaTrader5 package.
        raise MT5ExecutionError("MT5 analysis helpers are unavailable on this host.") from exc
    return TIMEFRAMES, analyze_timeframe, build_decision


def _build_position_risk_state(
    *,
    positions: list[Any],
    symbol: str,
) -> dict[str, Any]:
    def get_symbol(position: Any) -> str:
        if isinstance(position, dict):
            return str(position.get("symbol", ""))
        return str(getattr(position, "symbol", ""))

    return {
        "daily_loss_percent": None,
        "weekly_loss_percent": None,
        "drawdown_percent": None,
        "open_positions": len(positions),
        "same_symbol_positions": sum(
            1
            for position in positions
            if get_symbol(position) == symbol
        ),
    }


def _monitor_symbol(
    broker: MT5Broker,
    symbol: str,
    canonical_symbol: str,
    asset_class: str,
    opportunity_score: float,
    risk_state: dict[str, Any] | None = None,
    count: int = 120,
) -> dict[str, Any]:
    quality_engine = SignalQualityEngine()
    timeframes, analyze_timeframe, build_decision = _analysis_tools()

    results = {
        tf: analyze_timeframe(broker, symbol, mt5_tf, count)
        for tf, mt5_tf in timeframes.items()
    }

    decision, _, _, _ = build_decision(results)

    quality = quality_engine.evaluate(
        decision,
        decision.get("mtf_alignment", "UNKNOWN"),
    )

    quote = broker.quote(symbol)

    price = (
        quote.get("last")
        or quote.get("bid")
        or quote.get("ask")
        or 0.0
    )

    risk_engine = RiskScoreEngine()

    if risk_state is None:
        risk_payload = risk_engine.evaluate(
            risk_percent=0.50,
            daily_loss_percent=None,
            weekly_loss_percent=None,
            drawdown_percent=None,
            open_positions=None,
            same_symbol_positions=None,
            spread_ok=True,
            data_fresh=True,
            stop_loss_valid=True,
        )
    else:
        risk_payload = risk_engine.evaluate(**risk_state)

    return {
        "symbol": symbol,
        "canonical_symbol": canonical_symbol,
        "asset_class": asset_class,
        "opportunity_score": opportunity_score,
        "price": float(price),
        "spread_points": round(
            float(quote.get("spread_points", 0.0) or 0.0),
            2,
        ),
        "decision": decision,
        "quality": quality,
        "risk": risk_payload,
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
def market_briefing(language: str = "en") -> dict[str, Any]:
    return get_market_briefing(language=language)


@router.get("/atlas")
def atlas_dashboard_state() -> dict[str, Any]:
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

        # Read-only MT5 positions are loaded before symbol monitoring so the
        # dashboard can expose real position-count risk context.
        positions = broker.positions()

        symbols: list[dict[str, Any]] = []
        symbol_errors: list[dict[str, str]] = []

        for item in universe:
            try:
                symbol_payload = _monitor_symbol(
                    broker,
                    item.broker_symbol,
                    item.canonical_symbol,
                    item.asset_class,
                    item.opportunity_score,
                    risk_state=None,
                )

                # Do not fabricate account-history risk metrics.
                # Daily/weekly loss and drawdown remain None until a verified
                # history/equity source is connected.
                symbol_payload["position_risk_state"] = (
                    _build_position_risk_state(
                        positions=positions,
                        symbol=item.broker_symbol,
                    )
                )

                symbols.append(symbol_payload)

            except Exception as exc:
                symbol_errors.append(
                    {
                        "symbol": item.broker_symbol,
                        "error": str(exc),
                    }
                )
        pending_orders = _pending_orders()
        recent_trades = _recent_trade_history(days=7)

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
        real_money_ready = bool(account.get("real_money_execution_enabled", False))
        return {
            "status": "ONLINE",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": "REAL_MONEY_EXECUTION" if real_money_ready else "LIVE_DEMO",
            "account": _public_account(account, raw_account),
            "verified_live_account": account_type == "REAL",
            "symbols": symbols,
            "positions": public_positions,
            "pending_orders": pending_orders,
            "recent_trades": recent_trades,
            "open_positions": len(positions),
            "floating_position_pnl": round(sum(float(p.get("profit", 0.0) or 0.0) for p in positions), 2),
            "alerts": alerts,
            "symbol_errors": symbol_errors,
            "financial_market": financial_market,
            "services": {
                "mt5": "ONLINE",
                "supabase": journal_status,
                "execution_gate": "ENABLED" if real_money_ready else "DISABLED",
                "subscriber_access": "DEMO_VIEW",
                "financial_markets": financial_market["status"],
                "real_money_execution": "ENABLED" if real_money_ready else "DISABLED",
            },
            "disclaimer": (
                "Live demo telemetry and execution status. Real-money execution requires an approved REAL account, "
                "explicit owner acknowledgement, and broker trade permission. Past or current results do not guarantee future performance."
            ),
        }
    except MT5ExecutionError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    finally:
        broker.disconnect()
