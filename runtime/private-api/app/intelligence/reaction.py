from datetime import datetime, timezone


class MarketReactionEngine:

    HORIZONS = {
        "15m": 15 * 60,
        "1h": 60 * 60,
        "4h": 4 * 60 * 60,
        "24h": 24 * 60 * 60,
    }

    def _timestamp(self, value):
        if isinstance(value, (int, float)):
            return float(value)

        text = str(value)

        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        dt = datetime.fromisoformat(text)

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt.timestamp()

    def _nearest_index(
        self,
        candles,
        event_timestamp,
    ):
        target = self._timestamp(
            event_timestamp
        )

        best_index = None
        best_distance = None

        for index, candle in enumerate(candles):

            candle_time = (
                candle.get("open_time")
            )

            if candle_time is None:
                candle_time = candle.get(
                    "timestamp"
                )

            if candle_time is None:
                continue

            if isinstance(
                candle_time,
                (int, float),
            ):
                candle_timestamp = (
                    candle_time / 1000
                )

            else:
                candle_timestamp = (
                    self._timestamp(
                        candle_time
                    )
                )

            distance = abs(
                candle_timestamp - target
            )

            if (
                best_distance is None
                or distance < best_distance
            ):
                best_distance = distance
                best_index = index

        return best_index

    def _price_at_or_after(
        self,
        candles,
        start_index,
        seconds,
    ):
        if start_index is None:
            return None

        start_candle = candles[
            start_index
        ]

        start_time = (
            start_candle["open_time"]
            / 1000
        )

        target_time = (
            start_time + seconds
        )

        for candle in candles[
            start_index:
        ]:

            candle_time = (
                candle["open_time"]
                / 1000
            )

            if candle_time >= target_time:
                return float(
                    candle["close"]
                )

        return None

    def _reaction(
        self,
        event_price,
        future_price,
    ):
        if (
            event_price is None
            or future_price is None
        ):
            return None

        if event_price == 0:
            return None

        return (
            (
                future_price
                - event_price
            )
            / event_price
        ) * 100

    def analyze(
        self,
        event_timestamp,
        candles,
    ):
        if not candles:
            return {
                "status": "NO_DATA"
            }

        index = self._nearest_index(
            candles,
            event_timestamp,
        )

        if index is None:
            return {
                "status": "EVENT_NOT_FOUND"
            }

        event_price = float(
            candles[index]["close"]
        )

        reactions = {}

        for name, seconds in (
            self.HORIZONS.items()
        ):

            future_price = (
                self._price_at_or_after(
                    candles,
                    index,
                    seconds,
                )
            )

            reactions[name] = {
                "price": future_price,
                "return_percent": (
                    None
                    if future_price is None
                    else round(
                        self._reaction(
                            event_price,
                            future_price,
                        ),
                        4,
                    )
                ),
            }

        return {
            "status": "OK",
            "event_timestamp": (
                event_timestamp
            ),
            "event_candle_index": index,
            "event_price": event_price,
            "reactions": reactions,
        }


def classify_reaction(
    return_percent,
    threshold=0.25,
):
    """
    Classify market reaction.

    threshold is percentage movement.
    """

    if return_percent is None:
        return "UNKNOWN"

    if return_percent >= threshold:
        return "BULLISH"

    if return_percent <= -threshold:
        return "BEARISH"

    return "NEUTRAL"


if __name__ == "__main__":

    candles = []

    base_time = (
        1750000000000
    )

    base_price = 100000.0

    for i in range(30):

        candles.append({
            "open_time": (
                base_time
                + i * 60 * 60 * 1000
            ),
            "open": base_price,
            "high": base_price + 100,
            "low": base_price - 100,
            "close": base_price,
            "volume": 1.0,
        })

        base_price += 100

    event_time = (
        datetime.fromtimestamp(
            base_time / 1000,
            tz=timezone.utc,
        ).isoformat()
    )

    engine = MarketReactionEngine()

    result = engine.analyze(
        event_timestamp=event_time,
        candles=candles,
    )

    print()
    print(
        "MARKET REACTION TEST"
    )
    print("=" * 40)
    print(result)

    print()
    print(
        "1H CLASSIFICATION:"
    )

    one_hour = result[
        "reactions"
    ]["1h"]["return_percent"]

    print(
        classify_reaction(one_hour)
    )
