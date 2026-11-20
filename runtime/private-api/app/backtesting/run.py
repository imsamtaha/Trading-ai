from app.analysis.technical import analyze_candles
from app.analysis.structure import analyze_structure
from app.strategies.signal import generate_signal
from app.strategies.trade import create_trade_candidate

from app.backtesting.engine import BacktestEngine
from app.backtesting.historical import (
    fetch_historical_candles,
)


def strategy_signal(candles):

    try:

        technical = analyze_candles(
            candles
        )

        structure = analyze_structure(
            candles
        )

        signal = generate_signal(
            technical,
            structure,
        )

        trade = create_trade_candidate(
            signal,
            technical,
            account_balance=10000.0,
        )

        if trade.get("status") != "TRADE_CANDIDATE":
            return None

        return {
            "direction": trade["direction"],
            "entry": trade["entry"],
            "stop_loss": trade["stop_loss"],
            "take_profit": trade["take_profit"],
        }

    except Exception:
        return None


def run_backtest(
    symbol="BTCUSDT",
    interval="1h",
    candles_count=2000,
):

    print()
    print("=" * 60)
    print("TRADING AI HISTORICAL BACKTEST")
    print("=" * 60)

    print(f"Symbol: {symbol}")
    print(f"Interval: {interval}")
    print(
        f"Requested candles: "
        f"{candles_count}"
    )

    candles = fetch_historical_candles(
        symbol=symbol,
        interval=interval,
        total_candles=candles_count,
    )

    print(
        f"Downloaded candles: "
        f"{len(candles)}"
    )

    engine = BacktestEngine(
        initial_balance=10000.0,
        risk_per_trade=0.01,
    )

    results = engine.run(
        symbol=symbol,
        candles=candles,
        signal_function=strategy_signal,
        minimum_history=50,
    )

    print()
    print("===== RESULTS =====")

    for key, value in results.items():

        if key != "trades":
            print(
                f"{key}: {value}"
            )

    print()
    print(
        f"Closed trades: "
        f"{len(results['trades'])}"
    )

    return results


def main():

    run_backtest(
        symbol="BTCUSDT",
        interval="1h",
        candles_count=2000,
    )


if __name__ == "__main__":
    main()
