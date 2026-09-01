from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import MetaTrader5 as mt5

from app.analysis.structure import analyze_structure
from app.analysis.technical import analyze_candles
from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError
from app.intelligence.context import build_mtf_context
from app.intelligence.decision.engine import DecisionInput, UnifiedDecisionEngine
from app.intelligence.regime.engine import MarketRegimeEngine, MarketState
from app.strategies.signal import generate_signal

TIMEFRAMES = {
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


def build_decision(results: dict[str, dict]) -> tuple[dict, dict, dict]:
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
    return decision, regime, context


def main() -> int:
    args = parse_args()
    broker = MT5Broker(MT5Config.from_env())
    try:
        account = broker.connect()
        broker.symbol_info(args.symbol)
        results = {
            timeframe: analyze_timeframe(broker, args.symbol, mt5_timeframe, args.count)
            for timeframe, mt5_timeframe in TIMEFRAMES.items()
        }
        decision, regime, context = build_decision(results)

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
        }
        print(json.dumps(output, indent=2, default=str))
        return 0
    except MT5ExecutionError as exc:
        print(json.dumps({"status": "MT5_ERROR", "error": str(exc)}, indent=2))
        return 1
    finally:
        broker.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
