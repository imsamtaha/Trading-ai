import time
import requests


BINANCE_KLINES_URL = (
    "https://api.binance.com/api/v3/klines"
)


def fetch_historical_candles(
    symbol="BTCUSDT",
    interval="1h",
    total_candles=5000,
):
    """
    Download historical OHLCV candles.

    This is market-data collection only.
    It does not place orders.
    """

    all_candles = []

    end_time = None

    while len(all_candles) < total_candles:

        remaining = (
            total_candles
            - len(all_candles)
        )

        limit = min(
            remaining,
            1000,
        )

        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": limit,
        }

        if end_time is not None:
            params["endTime"] = end_time

        response = requests.get(
            BINANCE_KLINES_URL,
            params=params,
            timeout=20,
        )

        response.raise_for_status()

        rows = response.json()

        if not rows:
            break

        batch = []

        for row in rows:

            batch.append({
                "open_time": row[0],
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
                "close_time": row[6],
            })

        all_candles = (
            batch + all_candles
        )

        oldest_open_time = rows[0][0]

        end_time = (
            oldest_open_time - 1
        )

        if len(rows) < limit:
            break

        time.sleep(0.2)

    # Remove duplicates
    unique = {}

    for candle in all_candles:
        unique[
            candle["open_time"]
        ] = candle

    candles = list(
        unique.values()
    )

    candles.sort(
        key=lambda x: x["open_time"]
    )

    return candles[
        -total_candles:
    ]
