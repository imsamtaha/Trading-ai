from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from app.analysis.structure import analyze_structure
from app.analysis.technical import analyze_candles
from app.execution.auto import AutoExecutionCoordinator
from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError
from app.intelligence.decision.engine import DecisionInput, UnifiedDecisionEngine
from app.strategies.router import generate_strategy_candidate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ATLAS automatic MT5 execution worker")
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--interval", default="5m", choices=["5m", "15m", "30m", "1h"])
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--forever", action="store_true")
    parser.add_argument("--cycle-seconds", type=int, default=30)
    return parser.parse_args()


def _timeframe(interval: str) -> int:
    if mt5 is None:
        raise MT5ExecutionError("MetaTrader5 is available only on the Windows worker.")
    mapping = {
        "5m": mt5.TIMEFRAME_M5,
        "15m": mt5.TIMEFRAME_M15,
        "30m": mt5.TIMEFRAME_M30,
        "1h": mt5.TIMEFRAME_H1,
    }
    return mapping[interval]


def _decision(candidate: dict) -> dict:
    direction = candidate.get("direction")
    technical_score = {"LONG": 1.0, "SHORT": -1.0}.get(direction, 0.0)
    data = DecisionInput(
        technical_score=technical_score,
        macro_score=0.0,
        news_score=0.0,
        geopolitical_score=0.0,
        cross_asset_score=0.0,
        reaction_score=0.0,
        regime=str(candidate.get("regime", "TRANSITION")),
        conflict_score=0.0,
        volatility_score=0.0,
        event_risk_score=0.0,
    )
    return UnifiedDecisionEngine().analyze(data)


def run_cycle(symbol: str, interval: str, count: int) -> dict:
    broker = MT5Broker(MT5Config.from_env())
    coordinator = AutoExecutionCoordinator(broker=broker)
    try:
        account = broker.connect()
        candles = broker.candles(symbol, _timeframe(interval), count)
        if len(candles) < 50:
            raise MT5ExecutionError(f"{symbol}: at least 50 candles are required.")

        technical = analyze_candles(candles)
        structure = analyze_structure(candles)
        candidate_obj = generate_strategy_candidate(
            symbol,
            technical,
            structure,
            mode=os.getenv("ATLAS_STRATEGY_MODE", "BALANCED"),
            account_balance=float(account["equity"]),
        )

        if candidate_obj is None:
            return {
                "status": "NO_TRADE",
                "symbol": symbol,
                "reason": "No strategy candidate.",
                "runtime": coordinator.status(),
            }

        candidate = candidate_obj.to_dict()
        decision = _decision(candidate)

        if not candidate.get("qualified"):
            return {
                "status": "NO_TRADE",
                "symbol": symbol,
                "reason": "Candidate did not qualify.",
                "candidate": candidate,
                "decision": decision,
                "runtime": coordinator.status(),
            }

        execution = coordinator.execute_candidate(
            symbol=symbol,
            candidate=candidate,
            decision=decision,
            account=account,
        )
        return {
            "status": execution.get("status", "UNKNOWN"),
            "symbol": symbol,
            "candidate": candidate,
            "decision": decision,
            "execution": execution,
            "runtime": coordinator.status(),
        }
    finally:
        broker.disconnect()


def main() -> int:
    args = parse_args()
    if os.getenv("ATLAS_AUTO_EXECUTION_ENABLED", "false").lower() != "true":
        print(json.dumps({
            "status": "BLOCKED",
            "reason": "ATLAS_AUTO_EXECUTION_ENABLED=false",
        }))
        return 2

    if os.getenv("ATLAS_LIVE_TRADING", "false").lower() != "true":
        print(json.dumps({
            "status": "BLOCKED",
            "reason": "ATLAS_LIVE_TRADING=false",
        }))
        return 2

    while True:
        try:
            result = run_cycle(args.symbol.upper(), args.interval, args.count)
            print(json.dumps(result, indent=2, default=str), flush=True)
        except Exception as exc:
            print(json.dumps({"status": "ERROR", "error": str(exc)}, indent=2), flush=True)
            if not args.forever:
                return 1

        if not args.forever:
            return 0
        time.sleep(max(10, args.cycle_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
