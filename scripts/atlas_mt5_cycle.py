from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import MetaTrader5 as mt5
except ImportError:  # Allows pure decision logic and CI to run on non-Windows hosts.
    mt5 = None

import requests

from app.analysis.structure import analyze_structure
from app.analysis.technical import analyze_candles
from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError
from app.intelligence.confidence import SignalQualityEngine
from app.intelligence.context import build_mtf_context
from app.intelligence.decision.engine import DecisionInput, UnifiedDecisionEngine
from app.intelligence.regime.engine import MarketRegimeEngine, MarketState
from app.strategies.signal import generate_signal

TIMEFRAMES = {} if mt5 is None else {
    "5m": mt5.TIMEFRAME_M5,
    "15m": mt5.TIMEFRAME_M15,
    "30m": mt5.TIMEFRAME_M30,
    "1h": mt5.TIMEFRAME_H1,
}

TF_WEIGHTS = {"5m": 0.15, "15m": 0.20, "30m": 0.25, "1h": 0.40}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ATLAS MT5 dry-run analysis cycle")
    parser.add_argument("--symbol", default="EURUSD", help="Exact FxPro MT5 symbol, e.g. EURUSD or GOLD")
    parser.add_argument("--count", type=int, default=200, help="Number of candles per timeframe")
    return parser.parse_args()


def supabase_config() -> tuple[str | None, str | None]:
    url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SECRET_KEY")
    return url, key


def persist_to_supabase(symbol: str, account: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    url, key = supabase_config()
    if not url or not key:
        return {"status": "NOT_CONNECTED", "reason": "SUPABASE_URL or service key is not configured"}

    endpoint = f"{url.rstrip('/')}/rest/v1/atlas_execution_events"
    payload = {
        "symbol": symbol,
        "timeframe": "MTF",
        "decision": decision["decision"],
        "confidence": decision.get("execution_confidence", decision.get("confidence")),
        "risk_level": decision.get("risk_level"),
        "directional_score": decision.get("directional_score"),
        "directional_strength": decision.get("directional_strength"),
        "evidence_quality": decision.get("evidence_quality"),
        "execution_confidence": decision.get("execution_confidence"),
        "signal_quality": decision.get("signal_quality"),
        "mtf_score": decision.get("mtf_score"),
        "mtf_alignment": decision.get("mtf_alignment"),
        "regime": decision.get("regime"),
        "status": "DRY_RUN",
        "reason": "ATLAS MT5 analysis cycle",
        "payload": {
            "server": account.get("server"),
            "login": account.get("login"),
            "equity": account.get("equity"),
            "currency": account.get("currency"),
            "external_context": decision.get("external_context"),
        },
    }

    response = requests.post(
        endpoint,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        json=payload,
        timeout=10,
    )
    response.raise_for_status()
    return {"status": "PERSISTED", "rows": len(response.json()) if response.content else 1}


def analyze_timeframe(broker: MT5Broker, symbol: str, timeframe: int, count: int) -> dict:
    candles = broker.candles(symbol, timeframe, count)
    if len(candles) < 50:
        raise MT5ExecutionError(f"{symbol}: only {len(candles)} candles returned; at least 50 are required.")

    technical = analyze_candles(candles)
    structure = analyze_structure(candles)
    signal = generate_signal(technical, structure)
    signal_score = max(-1.0, min(1.0, (float(signal.get("score", 50)) - 50.0) / 50.0))

    return {
        "candles": len(candles),
        "technical": technical,
        "structure": {
            "structure": structure["structure"],
            "break_events": structure["break_events"],
            "liquidity_events": structure["liquidity_events"],
        },
        "signal": signal,
        "component": round(signal_score, 4),
    }


def build_decision(results: dict[str, dict]) -> tuple[dict, dict, dict, dict]:
    context = build_mtf_context(results, TF_WEIGHTS)

    regime_state = MarketState(
        trend_score=context["trend_score"],
        volatility_score=0.0,
        momentum_score=context["momentum_score"],
        volume_score=0.0,
        event_risk_score=0.0,
        risk_sentiment_score=0.0,
    )
    regime = MarketRegimeEngine().analyze(regime_state)

    decision_data = DecisionInput(
        technical_score=context["mtf_score"],
        macro_score=0.0,
        news_score=0.0,
        geopolitical_score=0.0,
        cross_asset_score=0.0,
        reaction_score=context["macd_score"],
        regime=regime["primary_regime"],
        conflict_score=context["conflict_score"],
        volatility_score=0.0,
        event_risk_score=0.0,
    )
    decision = UnifiedDecisionEngine().analyze(decision_data)
    decision.update({
        "mtf_score": context["mtf_score"],
        "mtf_alignment": "STRONG" if abs(context["mtf_score"]) >= 0.75 else "MODERATE" if abs(context["mtf_score"]) >= 0.45 else "WEAK" if abs(context["mtf_score"]) >= 0.20 else "MIXED",
        "timeframe_weights": TF_WEIGHTS,
        "technical_context": {
            "trend_score": context["trend_score"],
            "momentum_score": context["momentum_score"],
            "macd_score": context["macd_score"],
            "structure_score": context["structure_score"],
            "conflict_score": context["conflict_score"],
        },
        "external_context": {
            "macro": {"status": "NOT_CONNECTED", "score": 0.0},
            "news": {"status": "NOT_CONNECTED", "score": 0.0},
            "geopolitical": {"status": "NOT_CONNECTED", "score": 0.0},
            "cross_asset": {"status": "NOT_CONNECTED", "score": 0.0},
        },
    })
    quality = SignalQualityEngine().evaluate(decision, decision["mtf_alignment"])
    decision.update(quality)
    return decision, regime, context, quality


def main() -> int:
    load_dotenv(ROOT / ".env", override=False)
    if mt5 is None:
        print(json.dumps({"status": "ERROR", "error": "MetaTrader5 is available only on the Windows MT5 worker."}))
        return 1

    args = parse_args()
    broker = MT5Broker(MT5Config.from_env())
    try:
        account = broker.connect()
        broker.symbol_info(args.symbol)
        results = {
            timeframe: analyze_timeframe(broker, args.symbol, mt5_timeframe, args.count)
            for timeframe, mt5_timeframe in TIMEFRAMES.items()
        }
        decision, regime, context, quality = build_decision(results)
        persistence = persist_to_supabase(args.symbol, account, decision)

        output = {
            "mode": "DRY_RUN" if broker.config.dry_run else "LIVE_GATEWAY",
            "account": {
                "server": account["server"],
                "login": account["login"],
                "equity": account["equity"],
                "currency": account["currency"],
            },
            "symbol": args.symbol,
            "timeframes": results,
            "context": context,
            "regime": regime,
            "decision": decision,
            "signal_quality": quality,
            "persistence": persistence,
        }
        print(json.dumps(output, indent=2, default=str))
        return 0
    except (MT5ExecutionError, requests.RequestException) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, indent=2))
        return 1
    finally:
        broker.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
