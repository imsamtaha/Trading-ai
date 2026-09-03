from app.monitor.atlas_mt5 import AtlasMT5Monitor


if __name__ == "__main__":
    monitor = AtlasMT5Monitor(
        symbols=None,
        interval="5m",
        candle_limit=200,
        cycle_seconds=30,
        top_n=30,
    )
    monitor.run_forever()
