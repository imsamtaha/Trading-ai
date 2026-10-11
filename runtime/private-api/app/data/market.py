import requests
from datetime import datetime, timezone

BINANCE_API = "https://api.binance.com/api/v3"
YAHOO_API = "https://query1.finance.yahoo.com/v8/finance/chart"

ASSET_MAP = {
    # Commodities
    "GOLD": "GC=F",
    "XAUUSD": "GC=F",
    "SILVER": "SI=F",
    "XAGUSD": "SI=F",
    "OIL": "CL=F",
    "WTI": "CL=F",
    "BRENT": "BZ=F",
    "GAS": "NG=F",
    "NATGAS": "NG=F",

    # Forex
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "JPY=X",
    "USDCHF": "CHF=X",
    "AUDUSD": "AUDUSD=X",
    "USDCAD": "CAD=X",
    "NZDUSD": "NZDUSD=X",
    "EURGBP": "EURGBP=X",
    "GBPJPY": "GBPJPY=X",
}

CRYPTO_SUFFIXES = ("USDT", "USDC", "BUSD", "BTC", "ETH")


def _is_crypto(symbol: str) -> bool:
    symbol = symbol.upper()
    return symbol.endswith(CRYPTO_SUFFIXES)


def _yahoo_symbol(symbol: str) -> str:
    symbol = symbol.upper()
    return ASSET_MAP.get(symbol, symbol)


def _yahoo_interval(interval: str) -> str:
    mapping = {
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1h": "1h",
        "4h": "1h",
        "1d": "1d",
    }
    return mapping.get(interval, "1h")


def _yahoo_period(interval: str, limit: int) -> int:
    if interval == "1d":
        return max(limit * 86400 * 2, 86400 * 30)

    # Give Yahoo enough history for intraday candles.
    return max(limit * 3600 * 4, 86400 * 7)


def _get_crypto_price(symbol: str) -> dict:
    response = requests.get(
        f"{BINANCE_API}/ticker/price",
        params={"symbol": symbol.upper()},
        timeout=10,
    )

    response.raise_for_status()
    data = response.json()

    return {
        "symbol": data["symbol"],
        "price": float(data["price"]),
    }


def _get_yahoo_price(symbol: str) -> dict:
    yahoo_symbol = _yahoo_symbol(symbol)

    response = requests.get(
        f"{YAHOO_API}/{yahoo_symbol}",
        params={
            "range": "1d",
            "interval": "1m",
        },
        timeout=10,
        headers={"User-Agent": "Mozilla/5.0"},
    )

    response.raise_for_status()
    data = response.json()

    result = data["chart"]["result"][0]
    meta = result["meta"]

    price = meta.get("regularMarketPrice")

    if price is None:
        quotes = result.get("indicators", {}).get("quote", [])
        if not quotes:
            raise ValueError(f"No price data for {symbol}")

        closes = quotes[0].get("close", [])
        price = next(
            (value for value in reversed(closes) if value is not None),
            None,
        )

    if price is None:
        raise ValueError(f"No current price available for {symbol}")

    return {
        "symbol": symbol.upper(),
        "price": float(price),
    }


def get_price(symbol: str = "BTCUSDT") -> dict:
    symbol = symbol.upper()

    if _is_crypto(symbol):
        return _get_crypto_price(symbol)

    return _get_yahoo_price(symbol)


def _get_crypto_candles(
    symbol: str,
    interval: str,
    limit: int,
) -> dict:

    allowed_intervals = {
        "1m",
        "3m",
        "5m",
        "15m",
        "30m",
        "1h",
        "2h",
        "4h",
        "6h",
        "8h",
        "12h",
        "1d",
    }

    if interval not in allowed_intervals:
        raise ValueError(
            f"Unsupported crypto interval: {interval}"
        )

    if not 1 <= limit <= 1000:
        raise ValueError(
            "Limit must be between 1 and 1000."
        )

    response = requests.get(
        f"{BINANCE_API}/klines",
        params={
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": limit,
        },
        timeout=10,
    )

    response.raise_for_status()
    raw_candles = response.json()

    candles = []

    for candle in raw_candles:
        candles.append(
            {
                "open_time": candle[0],
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4]),
                "volume": float(candle[5]),
                "close_time": candle[6],
            }
        )

    return {
        "symbol": symbol.upper(),
        "interval": interval,
        "count": len(candles),
        "candles": candles,
    }


def _get_yahoo_candles(
    symbol: str,
    interval: str,
    limit: int,
) -> dict:

    yahoo_symbol = _yahoo_symbol(symbol)
    yahoo_interval = _yahoo_interval(interval)

    period = _yahoo_period(interval, limit)

    response = requests.get(
        f"{YAHOO_API}/{yahoo_symbol}",
        params={
            "period1": int(datetime.now(timezone.utc).timestamp()) - period,
            "period2": int(datetime.now(timezone.utc).timestamp()),
            "interval": yahoo_interval,
            "events": "history",
            "includeAdjustedClose": "true",
        },
        timeout=15,
        headers={"User-Agent": "Mozilla/5.0"},
    )

    response.raise_for_status()

    data = response.json()
    result = data["chart"]["result"][0]

    timestamps = result.get("timestamp", [])
    quotes = result.get("indicators", {}).get("quote", [])

    if not timestamps or not quotes:
        raise ValueError(f"No candle data for {symbol}")

    quote = quotes[0]

    candles = []

    for i, timestamp in enumerate(timestamps):
        if i >= len(quote["close"]):
            break

        close = quote["close"][i]

        if close is None:
            continue

        open_price = quote["open"][i]
        high = quote["high"][i]
        low = quote["low"][i]
        volume = quote["volume"][i]

        if (
            open_price is None
            or high is None
            or low is None
        ):
            continue

        candles.append(
            {
                "open_time": int(timestamp * 1000),
                "open": float(open_price),
                "high": float(high),
                "low": float(low),
                "close": float(close),
                "volume": float(volume or 0),
                "close_time": int(timestamp * 1000),
            }
        )

    # Yahoo does not provide native 4h candles.
    # Aggregate 1h candles into 4h candles.
    if interval == "4h":
        candles = _aggregate_candles(candles, 4)

    candles = candles[-limit:]

    return {
        "symbol": symbol.upper(),
        "interval": interval,
        "count": len(candles),
        "candles": candles,
    }


def _aggregate_candles(candles: list, group_size: int) -> list:
    if not candles:
        return []

    result = []

    for i in range(0, len(candles), group_size):
        group = candles[i:i + group_size]

        if len(group) < group_size:
            continue

        result.append(
            {
                "open_time": group[0]["open_time"],
                "open": group[0]["open"],
                "high": max(c["high"] for c in group),
                "low": min(c["low"] for c in group),
                "close": group[-1]["close"],
                "volume": sum(c["volume"] for c in group),
                "close_time": group[-1]["close_time"],
            }
        )

    return result


def get_candles(
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    limit: int = 100,
) -> dict:

    symbol = symbol.upper()

    if _is_crypto(symbol):
        return _get_crypto_candles(
            symbol,
            interval,
            limit,
        )

    return _get_yahoo_candles(
        symbol,
        interval,
        limit,
    )


if __name__ == "__main__":
    symbols = [
        "BTCUSDT",
        "ETHUSDT",
        "GOLD",
        "SILVER",
        "OIL",
        "GAS",
        "EURUSD",
    ]

    print("=== MULTI-ASSET MARKET TEST ===")

    for symbol in symbols:
        try:
            price = get_price(symbol)
            print(
                f"{symbol:10} "
                f"${price['price']}"
            )
        except Exception as exc:
            print(
                f"{symbol:10} ERROR: {exc}"
            )

    print("\n=== CANDLE TEST ===")

    for symbol in symbols:
        try:
            data = get_candles(
                symbol,
                "1h",
                5,
            )

            print(
                f"{symbol:10} "
                f"{data['count']} candles"
            )

        except Exception as exc:
            print(
                f"{symbol:10} ERROR: {exc}"
            )
