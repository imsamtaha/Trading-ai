import numpy as np


def find_swing_points(candles, left=2, right=2):
    highs = np.array([c["high"] for c in candles], dtype=float)
    lows = np.array([c["low"] for c in candles], dtype=float)

    swing_highs = []
    swing_lows = []

    for i in range(left, len(candles) - right):
        current_high = highs[i]
        current_low = lows[i]

        left_highs = highs[i - left:i]
        right_highs = highs[i + 1:i + right + 1]

        left_lows = lows[i - left:i]
        right_lows = lows[i + 1:i + right + 1]

        if current_high > np.max(left_highs) and current_high > np.max(right_highs):
            swing_highs.append({
                "index": i,
                "price": float(current_high),
                "time": candles[i]["open_time"],
            })

        if current_low < np.min(left_lows) and current_low < np.min(right_lows):
            swing_lows.append({
                "index": i,
                "price": float(current_low),
                "time": candles[i]["open_time"],
            })

    return swing_highs, swing_lows


def classify_swings(swing_highs, swing_lows):
    classified_highs = []
    classified_lows = []

    previous_high = None
    previous_low = None

    for point in swing_highs:
        if previous_high is None:
            label = "SH"
        elif point["price"] > previous_high:
            label = "HH"
        else:
            label = "LH"

        classified_highs.append({
            **point,
            "type": label,
        })

        previous_high = point["price"]

    for point in swing_lows:
        if previous_low is None:
            label = "SL"
        elif point["price"] > previous_low:
            label = "HL"
        else:
            label = "LL"

        classified_lows.append({
            **point,
            "type": label,
        })

        previous_low = point["price"]

    return classified_highs, classified_lows


def determine_structure(classified_highs, classified_lows):
    recent_highs = classified_highs[-3:]
    recent_lows = classified_lows[-3:]

    bullish_points = sum(
        1 for point in recent_highs + recent_lows
        if point["type"] in ("HH", "HL")
    )

    bearish_points = sum(
        1 for point in recent_highs + recent_lows
        if point["type"] in ("LH", "LL")
    )

    if bullish_points > bearish_points:
        return "bullish"

    if bearish_points > bullish_points:
        return "bearish"

    return "neutral"


def detect_breaks(candles, swing_highs, swing_lows):
    if len(candles) < 2:
        return []

    current_close = candles[-1]["close"]
    previous_close = candles[-2]["close"]

    events = []

    if swing_highs:
        latest_high = swing_highs[-1]

        if (
            previous_close <= latest_high["price"]
            and current_close > latest_high["price"]
        ):
            events.append({
                "type": "BOS_BULLISH",
                "level": latest_high["price"],
                "price": current_close,
            })

    if swing_lows:
        latest_low = swing_lows[-1]

        if (
            previous_close >= latest_low["price"]
            and current_close < latest_low["price"]
        ):
            events.append({
                "type": "BOS_BEARISH",
                "level": latest_low["price"],
                "price": current_close,
            })

    return events


def detect_liquidity_sweeps(candles, swing_highs, swing_lows):
    if not candles:
        return []

    latest = candles[-1]

    events = []

    if swing_highs:
        high_level = swing_highs[-1]["price"]

        if (
            latest["high"] > high_level
            and latest["close"] < high_level
        ):
            events.append({
                "type": "LIQUIDITY_SWEEP_HIGH",
                "level": high_level,
                "price": latest["close"],
            })

    if swing_lows:
        low_level = swing_lows[-1]["price"]

        if (
            latest["low"] < low_level
            and latest["close"] > low_level
        ):
            events.append({
                "type": "LIQUIDITY_SWEEP_LOW",
                "level": low_level,
                "price": latest["close"],
            })

    return events


def analyze_structure(candles):
    if len(candles) < 20:
        raise ValueError(
            "At least 20 candles are required for market-structure analysis."
        )

    swing_highs, swing_lows = find_swing_points(candles)

    classified_highs, classified_lows = classify_swings(
        swing_highs,
        swing_lows,
    )

    structure = determine_structure(
        classified_highs,
        classified_lows,
    )

    breaks = detect_breaks(
        candles,
        swing_highs,
        swing_lows,
    )

    sweeps = detect_liquidity_sweeps(
        candles,
        swing_highs,
        swing_lows,
    )

    return {
        "structure": structure,
        "swing_highs": classified_highs[-10:],
        "swing_lows": classified_lows[-10:],
        "break_events": breaks,
        "liquidity_events": sweeps,
    }
