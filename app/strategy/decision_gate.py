from __future__ import annotations

from app.strategies.signal import generate_signal
from app.strategies.trade import create_trade_candidate


def build_decision(mtf: dict, account_balance: float) -> dict:
    """Build a conservative decision from the existing strategy engines.

    A trade is only actionable when all configured timeframes agree on the same
    directional trend and the existing risk engine approves the candidate.
    """
    frames = mtf.get("timeframes", {})
    if not frames or mtf.get("errors"):
        return {
            "status": "WAIT",
            "reason": "Incomplete multi-timeframe data.",
            "mtf": mtf,
        }

    trends = [str(frame.get("trend", "neutral")).lower() for frame in frames.values()]
    bullish = sum(trend == "bullish" for trend in trends)
    bearish = sum(trend == "bearish" for trend in trends)
    total = len(trends)

    if bullish == total:
        direction = "LONG"
    elif bearish == total:
        direction = "SHORT"
    else:
        return {
            "status": "WAIT",
            "reason": "Higher-timeframe or execution-timeframe conflict.",
            "alignment": f"{max(bullish, bearish)}/{total}",
            "mtf": mtf,
        }

    execution_frame = frames.get("5m") or frames.get("15m") or next(iter(frames.values()))
    signal = generate_signal(
        {
            "trend": execution_frame.get("trend", "neutral"),
            "momentum": execution_frame.get("momentum", "unknown"),
            "macd_signal": execution_frame.get("macd_signal", "unknown"),
            "price": execution_frame.get("price"),
        },
        {"structure": execution_frame.get("structure", "neutral")},
    )

    if signal.get("direction") != direction:
        return {
            "status": "WAIT",
            "reason": "Execution-timeframe signal disagrees with MTF consensus.",
            "mtf": mtf,
            "signal": signal,
        }

    technical = {
        "price": execution_frame.get("price"),
        "indicators": {"atr_14": execution_frame.get("atr_14")},
    }
    # ATR is not currently exported by the MTF summary; require the full analysis
    # path to produce a trade candidate instead of fabricating volatility data.
    if not technical["price"] or not technical["indicators"]["atr_14"]:
        return {
            "status": "WAIT",
            "reason": "ATR/price unavailable for risk-based trade candidate.",
            "mtf": mtf,
            "signal": signal,
        }

    trade = create_trade_candidate(signal, technical, account_balance=account_balance)
    return {
        "status": "READY" if trade.get("status") == "TRADE_CANDIDATE" else "WAIT",
        "direction": direction,
        "alignment": f"{total}/{total}",
        "signal": signal,
        "trade": trade,
        "mtf": mtf,
    }
