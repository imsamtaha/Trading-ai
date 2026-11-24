import numpy as np


def sma(values, period):
    values = np.asarray(values, dtype=float)

    if len(values) < period:
        return None

    return float(np.mean(values[-period:]))


def ema(values, period):
    values = np.asarray(values, dtype=float)

    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)

    current = float(np.mean(values[:period]))

    for price in values[period:]:
        current = (float(price) - current) * multiplier + current

    return float(current)


def rsi(values, period=14):
    values = np.asarray(values, dtype=float)

    if len(values) < period + 1:
        return None

    changes = np.diff(values)

    gains = np.maximum(changes, 0)
    losses = np.maximum(-changes, 0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    for i in range(period, len(changes)):
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period

    if avg_loss == 0:
        return 100.0

    relative_strength = avg_gain / avg_loss

    return float(100 - (100 / (1 + relative_strength)))


def macd(values, fast_period=12, slow_period=26, signal_period=9):
    values = np.asarray(values, dtype=float)

    if len(values) < slow_period + signal_period:
        return None

    multiplier_fast = 2 / (fast_period + 1)
    multiplier_slow = 2 / (slow_period + 1)

    fast = float(np.mean(values[:fast_period]))
    slow = float(np.mean(values[:slow_period]))

    macd_values = []

    start = slow_period

    for price in values[start:]:
        fast = (float(price) - fast) * multiplier_fast + fast
        slow = (float(price) - slow) * multiplier_slow + slow
        macd_values.append(fast - slow)

    if len(macd_values) < signal_period:
        return None

    signal_multiplier = 2 / (signal_period + 1)
    signal = float(np.mean(macd_values[:signal_period]))

    for value in macd_values[signal_period:]:
        signal = (float(value) - signal) * signal_multiplier + signal

    current_macd = float(macd_values[-1])

    return {
        "macd": current_macd,
        "signal": float(signal),
        "histogram": current_macd - signal,
    }


def atr(highs, lows, closes, period=14):
    highs = np.asarray(highs, dtype=float)
    lows = np.asarray(lows, dtype=float)
    closes = np.asarray(closes, dtype=float)

    if len(closes) < period + 1:
        return None

    true_ranges = []

    for i in range(1, len(closes)):
        true_range = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )

        true_ranges.append(true_range)

    if len(true_ranges) < period:
        return None

    current_atr = float(np.mean(true_ranges[:period]))

    for value in true_ranges[period:]:
        current_atr = (
            ((current_atr * (period - 1)) + value) / period
        )

    return float(current_atr)


def support_resistance(highs, lows, lookback=20):
    highs = np.asarray(highs, dtype=float)
    lows = np.asarray(lows, dtype=float)

    if len(highs) < lookback:
        return None

    recent_highs = highs[-lookback:]
    recent_lows = lows[-lookback:]

    return {
        "resistance": float(np.max(recent_highs)),
        "support": float(np.min(recent_lows)),
    }


def analyze_candles(candles):
    if len(candles) < 50:
        raise ValueError(
            "At least 50 candles are required for technical analysis."
        )

    closes = np.array(
        [c["close"] for c in candles],
        dtype=float,
    )

    highs = np.array(
        [c["high"] for c in candles],
        dtype=float,
    )

    lows = np.array(
        [c["low"] for c in candles],
        dtype=float,
    )

    volumes = np.array(
        [c["volume"] for c in candles],
        dtype=float,
    )

    current_price = float(closes[-1])

    ema_20 = ema(closes, 20)
    ema_50 = ema(closes, 50)
    rsi_14 = rsi(closes, 14)
    macd_data = macd(closes)
    atr_14 = atr(highs, lows, closes, 14)
    levels = support_resistance(highs, lows, 20)

    average_volume = float(np.mean(volumes[-20:]))
    current_volume = float(volumes[-1])

    if ema_20 is not None and ema_50 is not None:
        if current_price > ema_20 > ema_50:
            trend = "bullish"
        elif current_price < ema_20 < ema_50:
            trend = "bearish"
        else:
            trend = "neutral"
    else:
        trend = "unknown"

    if rsi_14 is not None:
        if rsi_14 >= 70:
            momentum = "overbought"
        elif rsi_14 <= 30:
            momentum = "oversold"
        elif rsi_14 >= 50:
            momentum = "bullish"
        else:
            momentum = "bearish"
    else:
        momentum = "unknown"

    if macd_data:
        if macd_data["histogram"] > 0:
            macd_signal = "bullish"
        elif macd_data["histogram"] < 0:
            macd_signal = "bearish"
        else:
            macd_signal = "neutral"
    else:
        macd_signal = "unknown"

    volume_state = (
        "high"
        if current_volume > average_volume * 1.5
        else "normal"
    )

    return {
        "price": current_price,
        "trend": trend,
        "momentum": momentum,
        "macd_signal": macd_signal,
        "volume_state": volume_state,
        "indicators": {
            "ema_20": ema_20,
            "ema_50": ema_50,
            "rsi_14": rsi_14,
            "macd": macd_data,
            "atr_14": atr_14,
        },
        "levels": levels,
    }
