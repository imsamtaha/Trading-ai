"""Execute the ATLAS analysis and paper-ledger loop without MetaTrader 5.

This runner feeds *locally generated synthetic candles* through the same
production code paths the Windows demo worker uses:

    candles -> technical -> structure -> strategy candidate
            -> unified decision engine -> risk gate -> paper ledger
            -> simulated stop/target exits -> demo readiness report

It exists so the deterministic pipeline can be executed and reviewed on any
host (Linux, CI, a laptop without MT5) and so a sandbox/network outage is never
mistaken for a broken engine.

Every number below is SYNTHETIC. Nothing here is market data, a broker fill, or
evidence of performance. The ledger it writes is separate from the MT5 demo
ledger and is only used for pipeline verification.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analysis.structure import analyze_structure
from app.analysis.technical import analyze_candles
from app.intelligence.decision.engine import DecisionInput, UnifiedDecisionEngine
from app.paper_trading.mt5_ledger import MT5PaperLedger, PaperLedgerError
from app.paper_trading.readiness import evaluate_demo_readiness
from app.risk.manager import calculate_risk
from app.strategies.router import generate_strategy_candidate

DATA_SOURCE = "SYNTHETIC_LOCAL"

# Anchor price and per-bar volatility for the public ATLAS watchlist.
WATCHLIST = {
    "XAUUSD": (2400.0, 0.0016),
    "XAGUSD": (28.0, 0.0022),
    "NGAS": (2.60, 0.0032),
    "EURUSD": (1.0850, 0.0006),
    "SOLUSDT": (150.0, 0.0055),
    "XRPUSDT": (0.5200, 0.0048),
}

TIMEFRAME_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
}


def synthetic_candles(symbol: str, interval: str, count: int, seed: int) -> list[dict]:
    """Deterministic random-walk OHLC bars, one continuous series per symbol.

    Reproducible for a given seed. Callers must slice this single series so a
    follow-up window continues from the analysis window's last close instead of
    restarting at the anchor price.
    """
    if interval not in TIMEFRAME_MS:
        raise SystemExit(f"Unsupported interval: {interval}")
    anchor, vol = WATCHLIST.get(symbol.upper(), (100.0, 0.002))
    rng = random.Random(f"atlas-offline::{seed}::{symbol.upper()}")
    step = TIMEFRAME_MS[interval]
    now = int(datetime.now(timezone.utc).timestamp() * 1000)
    start = now - count * step

    # Per-symbol drift phase keeps the watchlist from moving in lockstep.
    phase = rng.random() * 60.0
    price = anchor
    candles: list[dict] = []
    for index in range(count):
        drift = math.sin((index + phase) / 17.0) * vol * 0.35
        shock = rng.gauss(0.0, vol)
        open_price = price
        close_price = max(open_price * (1.0 + drift + shock), 1e-8)
        wick = abs(rng.gauss(0.0, vol)) * open_price
        high = max(open_price, close_price) + wick
        low = max(min(open_price, close_price) - wick, 1e-8)
        candles.append({
            "open_time": start + index * step,
            "open": round(open_price, 8),
            "high": round(high, 8),
            "low": round(low, 8),
            "close": round(close_price, 8),
            "volume": float(round(abs(rng.gauss(250, 60)) + 1, 2)),
            "close_time": start + index * step + step - 1,
        })
        price = close_price
    return candles


def decision_from_candidate(engine: UnifiedDecisionEngine, candidate: dict) -> dict:
    """Mirror AtlasMT5Monitor._decision_from_candidate: strategy -> decision gate."""
    direction = candidate.get("direction")
    return engine.analyze(DecisionInput(
        technical_score={"LONG": 1.0, "SHORT": -1.0}.get(direction, 0.0),
        macro_score=0.0,
        news_score=0.0,
        geopolitical_score=0.0,
        cross_asset_score=0.0,
        reaction_score=0.0,
        regime=candidate.get("regime", "TRANSITION"),
        conflict_score=0.0,
        volatility_score=0.0,
        event_risk_score=0.0,
    ))


def rebase_levels(candidate: dict, entry: float) -> tuple[float, float]:
    """Keep the candidate's ATR geometry but re-anchor it to the executed price."""
    structural_entry = float(candidate["entry"])
    offset_sl = float(candidate["stop_loss"]) - structural_entry
    offset_tp = float(candidate["take_profit"]) - structural_entry
    return entry + offset_sl, entry + offset_tp


def run_symbol(engine: UnifiedDecisionEngine, ledger: MT5PaperLedger, *, symbol: str,
               interval: str, candles: list[dict], mode: str, equity: float) -> dict:
    technical = analyze_candles(candles)
    structure = analyze_structure(candles)
    candidate_obj = generate_strategy_candidate(
        symbol, technical, structure, mode=mode, account_balance=equity
    )
    candidate = candidate_obj.to_dict() if candidate_obj else None
    decision = decision_from_candidate(engine, candidate or {})

    event: dict = {
        "symbol": symbol,
        "timeframe": interval,
        "price": technical.get("price"),
        "trend": technical.get("trend"),
        "momentum": technical.get("momentum"),
        "structure": structure.get("structure"),
        "candidate": candidate,
        "decision": decision,
        "status": "NO_TRADE",
        "reason": "",
    }

    if candidate is None:
        event["reason"] = "No strategy setup qualified for scoring."
        return event
    if not candidate.get("qualified"):
        event["reason"] = "Candidate failed confidence or risk qualification."
        return event

    expected = "BUY" if candidate["direction"] == "LONG" else "SELL"
    if decision.get("decision") != expected:
        event["reason"] = "Unified decision gate did not confirm the strategy direction."
        return event
    if ledger.has_open_position(symbol):
        event["reason"] = "A simulated position is already open for this symbol."
        event["status"] = "SKIPPED"
        return event

    # Rebase to the last synthetic close and re-run the authoritative risk gate.
    entry = float(technical["price"])
    stop_loss, take_profit = rebase_levels(candidate, entry)
    base_risk = (candidate.get("metadata") or {}).get("risk", {})
    risk = calculate_risk(
        direction=candidate["direction"],
        entry=entry,
        stop_loss=stop_loss,
        take_profit=take_profit,
        account_balance=equity,
        risk_percent=float(base_risk.get("risk_percent") or 0.5),
    )
    if not risk.get("approved", False):
        event["reason"] = str(risk.get("reason", "Risk gate rejected the simulated trade."))
        event["risk"] = risk
        return event

    try:
        trade = ledger.open_trade(
            symbol=symbol,
            direction=candidate["direction"],
            entry=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=float(risk.get("position_size") or 0.0),
            risk=risk,
            strategy=str(candidate["strategy"]),
            confidence=float(candidate["confidence"]),
            timeframe=interval,
            decision=decision,
        )
    except PaperLedgerError as exc:
        event["status"] = "SKIPPED"
        event["reason"] = str(exc)
        event["risk"] = risk
        return event

    event.update({
        "status": "PAPER_TRADE_OPENED",
        "reason": "Strategy, decision and risk gates approved a simulated entry.",
        "risk": risk,
        "trade": trade,
    })
    return event


def settle(ledger: MT5PaperLedger, *, follow_up: dict[str, list[dict]]) -> list[dict]:
    """Walk synthetic follow-up quotes through the ledger's stop/target exits.

    Fill model: each follow-up bar is offered as one quote at its close, with no
    spread. That mirrors the production worker polling a live quote each cycle
    and closing on the crossing price, so a stop can settle slightly beyond
    -1R. Slippage, gaps and commissions are not modelled.
    """
    closed: list[dict] = []
    for symbol, bars in follow_up.items():
        if not ledger.has_open_position(symbol):
            continue
        for candle in bars:
            quote = float(candle["close"])
            closed.extend(ledger.close_due_positions(symbol, bid=quote, ask=quote))
            if not ledger.has_open_position(symbol):
                break
    return closed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one offline ATLAS pipeline cycle.")
    parser.add_argument("--symbols", default=",".join(WATCHLIST))
    parser.add_argument("--interval", default="5m", choices=sorted(TIMEFRAME_MS))
    parser.add_argument("--candles", type=int, default=200)
    parser.add_argument("--mode", default="BALANCED", choices=["CONSERVATIVE", "BALANCED", "ACTIVE"])
    parser.add_argument("--account-equity", type=float, default=10000.0)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--settle-bars", type=int, default=200)
    parser.add_argument("--ledger", default="data/atlas_offline_ledger.json")
    parser.add_argument("--reset-ledger", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if not symbols:
        raise SystemExit("At least one symbol is required.")

    ledger_path = Path(args.ledger)
    if args.reset_ledger and ledger_path.exists():
        ledger_path.unlink()
    ledger = MT5PaperLedger(str(ledger_path))
    engine = UnifiedDecisionEngine()

    analysis_bars = max(args.candles, 60)
    settle_bars = max(args.settle_bars, 1)
    events = []
    follow_up: dict[str, list[dict]] = {}
    for symbol in symbols:
        # One continuous series: the analysis window, then the quote window.
        series = synthetic_candles(
            symbol, args.interval, analysis_bars + settle_bars, args.seed
        )
        follow_up[symbol] = series[analysis_bars:]
        events.append(run_symbol(
            engine, ledger, symbol=symbol, interval=args.interval,
            candles=series[:analysis_bars], mode=args.mode, equity=args.account_equity,
        ))

    closed = settle(ledger, follow_up=follow_up)
    readiness = evaluate_demo_readiness(ledger.closed_trades())

    counts: dict[str, int] = {}
    for event in events:
        counts[event["status"]] = counts.get(event["status"], 0) + 1

    report = {
        "runner": "atlas_offline_cycle",
        "mode": "PAPER_DEMO",
        "data_source": DATA_SOURCE,
        "synthetic_data": True,
        "live_orders_sent": False,
        "atlas_live_trading": os.getenv("ATLAS_LIVE_TRADING", "false"),
        "fill_model": "synthetic bar-close quote, zero spread, no slippage or commissions",
        "readiness_scope": (
            "Smoke-test bookkeeping only. A handful of synthetic trades cannot "
            "support any performance conclusion."
        ),
        "as_of": datetime.now(timezone.utc).isoformat(),
        "config": {
            "symbols": symbols, "interval": args.interval, "candles": args.candles,
            "strategy_mode": args.mode, "account_equity": args.account_equity,
            "seed": args.seed,
        },
        "summary": {
            "symbols_evaluated": len(events),
            "status_counts": counts,
            "trades_opened": sum(1 for e in events if e["status"] == "PAPER_TRADE_OPENED"),
            "trades_settled": len(closed),
            "ledger": ledger.summary(),
        },
        "readiness": readiness,
        "events": events,
        "closed_trades": closed,
        "disclaimer": (
            "Synthetic local data executed through the paper-only pipeline. "
            "Not market data, not broker fills, not a performance claim."
        ),
    }
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
