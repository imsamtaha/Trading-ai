"""Portfolio correlations from aligned, completed price bars; no tick-volume proxy."""
from datetime import datetime, timezone
from math import isfinite
import numpy as np


def measure_correlations(symbol, open_symbols, histories, *, limit, snapshot_id, as_of, bar_seconds=300, minimum_samples=30):
    now = datetime.fromisoformat(str(as_of).replace("Z", "+00:00"))
    if now.tzinfo is None or not 0 < float(limit) <= 1 or not isfinite(float(limit)):
        raise ValueError("Explicit finite correlation policy and timezone are required")
    if type(bar_seconds) is not int or not 1 <= bar_seconds <= 86400:
        raise ValueError("Invalid bar interval")
    if type(minimum_samples) is not int or minimum_samples < 30:
        raise ValueError("At least 30 aligned returns are required")
    end = now.astimezone(timezone.utc).timestamp() * 1000
    symbols = {symbol, *open_symbols}
    series = {}
    for key in symbols:
        rows = histories.get(key)
        if not rows:
            raise ValueError("Correlation history unavailable")
        prices = {}
        for row in rows:
            stamp, close = float(row["open_time"]), float(row["close"])
            if not isfinite(stamp) or not isfinite(close) or close <= 0 or stamp in prices:
                raise ValueError("Invalid correlation history")
            if stamp > end:
                raise ValueError("Correlation bar opens in the future; verify broker timestamp normalization")
            if stamp + bar_seconds * 1000 <= end:
                prices[stamp] = close
        series[key] = prices
    common = sorted(set.intersection(*(set(values) for values in series.values())))
    if len(common) < minimum_samples + 1 or end - (common[-1] + bar_seconds * 1000) > bar_seconds * 2000:
        raise ValueError("Insufficient or stale aligned correlation history")
    # Adjacent timestamps must represent adjacent completed bars; missing gaps
    # cannot be compared as if they were one-bar returns.
    pairs = [(a, b) for a, b in zip(common, common[1:]) if b - a == bar_seconds * 1000]
    if len(pairs) < minimum_samples:
        raise ValueError("Insufficient aligned returns")
    returns = {key: np.array([np.log(values[b]) - np.log(values[a]) for a, b in pairs])
               for key, values in series.items()}
    if any(not np.isfinite(values).all() or np.std(values) <= 1e-12 for values in returns.values()):
        raise ValueError("Return variance unavailable")
    coefficients = {key: float(np.clip(np.corrcoef(returns[symbol], returns[key])[0, 1], -1, 1))
                    for key in set(open_symbols)}
    if not all(isfinite(value) for value in coefficients.values()):
        raise ValueError("Correlation unavailable")
    return {"symbol": symbol, "snapshot_id": snapshot_id, "limit": float(limit),
            "sample_count": len(pairs), "coefficients": coefficients,
            "available_at": now.isoformat(), "bar_seconds": bar_seconds,
            "last_bar_closed_at": datetime.fromtimestamp((common[-1] + bar_seconds * 1000) / 1000, timezone.utc).isoformat(),
            "source": "completed_bars", "method": "pearson_log_returns"}
