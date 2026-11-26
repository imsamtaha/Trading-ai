from app.database.db import initialize_database
from app.database.repository import create_account
from app.monitor.loop import PaperTradingMonitor


def main():

    initialize_database()

    account_id = 3

    monitor = PaperTradingMonitor(
        account_id=account_id,
        symbols=[
            "BTCUSDT",
        ],
        interval="1h",
        candle_limit=100,
        cycle_seconds=60,
    )

    monitor.run_forever()


if __name__ == "__main__":
    main()
