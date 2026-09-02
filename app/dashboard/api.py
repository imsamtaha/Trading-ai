from __future__ import annotations

import os
from typing import Any

import MetaTrader5 as mt5
from fastapi import APIRouter, HTTPException

from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError
from app.intelligence.confidence import SignalQualityEngine
from app.integrations.supabase_journal import SupabaseJournalError, SupabaseSignalJournal
from scripts.atlas_mt5_cycle import TIMEFRAMES, analyze_timeframe, build_decision

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
SYMBOLS = ["GOLD", "SILVER", "NAT.GAS", "EURUSD", "XRP", "SOLANA"]


def _monitor_once(symbol: str, count: int = 120) -> dict[str, Any]:
    broker = MT5Broker(MT5Config.from_env())
    quality_engine = SignalQualityEngine()
    try:
        account = broker.connect()
        results = {
            tf: analyze_timeframe(broker, symbol, mt5_tf, count)
            for tf, mt5_tf in TIMEFRAMES.items()
        }
        decision = build_decision(results)
        quality = quality_engine.evaluate(decision, decision.get("mtf_alignment", "UNKNOWN"))
        tick = mt5.symbol_info_tick(symbol)
        return {
            "symbol": symbol,
            "price": float(tick.last or tick.bid or tick.ask or 0.0) if tick else 0.0,
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
            "account": {
                "server": account["server"],
                "login": account["login"],
                "balance": account["balance"],
                "equity": account["equity"],
                "currency": account["currency"],
            },
        }
    finally:
        broker.disconnect()


@router.get("/atlas")
def atlas_dashboard_state() -> dict[str, Any]:
    try:
        symbols = [_monitor_once(symbol) for symbol in SYMBOLS]
        alerts = [
            {
                "symbol": item["symbol"],
                "type": "signal",
                "message": f"{item['decision']['decision']} · score {item['decision']['score']} · confidence {item['quality']['execution_confidence']}",
            }
            for item in symbols
            if item["decision"]["decision"] in {"BUY", "SELL", "NO_TRADE"}
        ]
        first = symbols[0]["account"] if symbols else {}
        journal_status = "UNKNOWN"
        try:
            journal = SupabaseSignalJournal()
            journal_status = "READY"
        except SupabaseJournalError:
            journal_status = "NOT_CONFIGURED"
        return {
            "status": "ONLINE",
            "mode": "DRY_RUN" if os.getenv("ATLAS_LIVE_TRADING", "false").lower() != "true" else "LIVE_GATEWAY",
            "broker": "FxPro",
            "server": first.get("server"),
            "account": first,
            "symbols": symbols,
            "alerts": alerts,
            "services": {
                "mt5": "ONLINE",
                "supabase": journal_status,
                "live_trading": os.getenv("ATLAS_LIVE_TRADING", "false").lower() == "true",
            },
        }
    except MT5ExecutionError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
