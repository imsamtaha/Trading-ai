from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow `python scripts/atlas_mt5_cycle.py` from the repository root.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import MetaTrader5 as mt5

from app.analysis.structure import analyze_structure
from app.analysis.technical import analyze_candles
from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError
from app.intelligence.decision.engine import DecisionInput, UnifiedDecisionEngine
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
    parser.add_argument(
        "--symbol",
        default="EURUSD",
        help="Exact FxPro MT5 symbol, e.g. EURUSD or GOLD",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=200,
        help="Number of candles per timeframe",
    )
    return parser.parse_args()


def side_value(value: str | None) -> float:
    return {"LONG": 1.0, "SHORT": -1.0}.get(str(value).upper(), 0.0)


def timeframe_component(analysis: dict, signal: dict) -> float:
    score = side_value(signal.get("direction")) * 0.50
    score += side_value(analysis["technical"].get("trend")) * 0.25
    score += side_value(analysis["technical"].get("momentum")) * 0.15
    score += side_value(analysis["structure"].get("structure")) * 0.10
    return max(-1.0, min(1.0, score))


def alignment_label(score: float) -> str:
    magnitude = abs(score)
    if magnitude >= 0.75:
        return "STRONG"
    if magnitude >= 0.45:
        return "MODERATE"
    if magnitude >= 0.20:
        return "WEAK"
    return "MIXED"


def analyze_timeframe(broker: MT5Broker, symbol: str, timeframe: int, count: int) -> dict:
    candles = broker.candles(symbol, timeframe, count)
    if len(candles) < 50:
        raise MT5ExecutionError(
            f"{symbol}: only {len(candles)} candles returned; at least 50 are required."
        )

    technical = analyze_candles(candles)
    structure = analyze_structure(candles)
    signal = generate_signal(technical, structure)
    component = timeframe_component(
        {"technical": technical, "structure": structure}, signal
    )

    return {
        "candles": len(candles),
        "technical": technical,
        "structure": {
            "structure": structure["structure"],
            "break_events": structure["break_events"],
            "liquidity_events": structure["liquidity_events"],
        },
        "signal": signal,
        "component": component,
    }


def build_decision(results: dict[str, dict]) -> dict:
    mtf_score = sum(results[tf]["component"] * TF_WEIGHTS[tf] for tf in TF_WEIGHTS)
    # The contextual providers are intentionally neutral until explicitly wired.
    data = DecisionInput(
        technical_score=mtf_score,
        macro_score=0.0,
        news_score=0.0,
        geopolitical_score=0.0,
        cross_asset_score=0.0,
        reaction_score=0.0,
        regime="TRANSITION",
        conflict_score=0.0,
        volatility_score=0.0,
        event_risk_score=0.0,
    )
    decision = UnifiedDecisionEngine().analyze(data)
    decision["mtf_score"] = round(mtf_score, 4)
    decision["mtf_alignment"] = alignment_label(mtf_score)
    decision["timeframe_weights"] = TF_WEIGHTS
    return decision


def main() -> int:
    args = parse_args()
    broker = MT5Broker(MT5Config.from_env())

    try:
        account = broker.connect()
        broker.symbol_info(args.symbol)

        results = {
            timeframe: analyze_timeframe(
                broker, args.symbol, mt5_timeframe, args.count
            )
            for timeframe, mt5_timeframe in TIMEFRAMES.items()
        }
        decision = build_decision(results)

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
