import time
from datetime import datetime, timezone

from app.data.market import get_candles, get_price
from app.analysis.technical import analyze_candles
from app.analysis.structure import analyze_structure
from app.strategies.signal import generate_signal
from app.strategies.trade import create_trade_candidate
from app.paper_trading.engine import PersistentPaperTradingEngine


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class PaperTradingMonitor:

    def __init__(
        self,
        account_id: int,
        symbols=None,
        interval="1h",
        candle_limit=100,
        cycle_seconds=60,
    ):
        self.account_id = account_id
        self.symbols = symbols or ["BTCUSDT"]
        self.interval = interval
        self.candle_limit = candle_limit
        self.cycle_seconds = cycle_seconds

        self.engine = PersistentPaperTradingEngine(
            account_id
        )

        self.running = False

    def analyze_symbol(self, symbol):

        market_data = get_candles(
            symbol=symbol,
            interval=self.interval,
            limit=self.candle_limit,
        )

        candles = market_data["candles"]

        technical = analyze_candles(candles)

        structure = analyze_structure(candles)

        signal = generate_signal(
            technical,
            structure,
        )

        trade = create_trade_candidate(
            signal,
            technical,
            account_balance=self.engine.account()["balance"],
        )

        return {
            "symbol": symbol,
            "market": market_data,
            "technical": technical,
            "structure": structure,
            "signal": signal,
            "trade": trade,
        }

    def get_market_prices(self):

        prices = {}

        for symbol in self.symbols:
            data = get_price(symbol)
            prices[symbol] = float(data["price"])

        return prices

    def monitor_positions(self):

        positions = self.engine.positions()

        if not positions:
            return []

        events = []

        for position in positions:

            try:
                market = get_candles(
                    position["symbol"],
                    self.interval,
                    2,
                )

                latest = market["candles"][-1]

                high = latest["high"]
                low = latest["low"]

                exit_price = None
                reason = None

                if position["direction"] == "LONG":

                    if low <= position["stop_loss"]:
                        exit_price = position["stop_loss"]
                        reason = "STOP_LOSS"

                    elif high >= position["take_profit"]:
                        exit_price = position["take_profit"]
                        reason = "TAKE_PROFIT"

                elif position["direction"] == "SHORT":

                    if high >= position["stop_loss"]:
                        exit_price = position["stop_loss"]
                        reason = "STOP_LOSS"

                    elif low <= position["take_profit"]:
                        exit_price = position["take_profit"]
                        reason = "TAKE_PROFIT"

                if exit_price is not None:

                    result = self.engine.close_position(
                        position_id=position["id"],
                        exit_price=exit_price,
                        reason=reason,
                    )

                    events.append(result)

            except Exception as exc:

                events.append({
                    "symbol": position["symbol"],
                    "error": str(exc),
                })

        return events

    def evaluate_new_trades(self):

        positions = self.engine.positions()

        open_symbols = {
            position["symbol"]
            for position in positions
        }

        results = []

        for symbol in self.symbols:

            if symbol in open_symbols:
                results.append({
                    "symbol": symbol,
                    "status": "SKIPPED",
                    "reason": "Position already open.",
                })
                continue

            try:

                analysis = self.analyze_symbol(symbol)

                trade = analysis["trade"]

                if trade["status"] != "TRADE_CANDIDATE":

                    results.append({
                        "symbol": symbol,
                        "status": "NO_TRADE",
                        "reason": trade.get(
                            "reason",
                            "No valid setup.",
                        ),
                    })

                    continue

                position = self.engine.open_position(
                    symbol=symbol,
                    direction=trade["direction"],
                    entry=trade["entry"],
                    stop_loss=trade["stop_loss"],
                    take_profit=trade["take_profit"],
                    position_size=trade["risk"]["position_size"],
                )

                results.append({
                    "symbol": symbol,
                    "status": "PAPER_TRADE_OPENED",
                    "position": position,
                })

            except Exception as exc:

                results.append({
                    "symbol": symbol,
                    "status": "ERROR",
                    "error": str(exc),
                })

        return results

    def run_cycle(self):

        print()
        print("=" * 60)
        print(f"TRADING AI CYCLE — {utc_now()}")
        print("=" * 60)

        # -------------------------------------------------
        # ACCOUNT + EQUITY
        # -------------------------------------------------

        print("\nACCOUNT")

        account = self.engine.account()

        print(
            f"Balance: ${account['balance']:.2f}"
        )

        try:

            market_prices = self.get_market_prices()

            equity = self.engine.calculate_equity(
                market_prices
            )

            print(
                f"Unrealized P&L: "
                f"${equity['unrealized_pnl']:.2f}"
            )

            print(
                f"Equity: "
                f"${equity['equity']:.2f}"
            )

            print(
                f"Exposure: "
                f"${equity['exposure']:.2f}"
            )

            for position in equity["positions"]:

                print(
                    f"{position['symbol']} "
                    f"{position['direction']} "
                    f"@ {position['current_price']:.2f} "
                    f"| P&L: "
                    f"${position['unrealized_pnl']:.2f}"
                )

        except Exception as exc:

            print(
                f"Equity calculation error: {exc}"
            )

        # -------------------------------------------------
        # POSITION MONITOR
        # -------------------------------------------------

        print("\nPOSITION MONITOR")

        position_events = self.monitor_positions()

        if position_events:

            for event in position_events:
                print(event)

        else:

            print("No position events.")

        # -------------------------------------------------
        # SIGNAL MONITOR
        # -------------------------------------------------

        print("\nSIGNAL MONITOR")

        trade_events = self.evaluate_new_trades()

        for event in trade_events:
            print(event)

        # -------------------------------------------------
        # FINAL STATE
        # -------------------------------------------------

        print("\nOPEN POSITIONS")

        positions = self.engine.positions()

        if positions:
            for position in positions:
                print(position)
        else:
            print("No open positions.")

        print("\nACCOUNT")

        final_account = self.engine.account()

        print(
            f"Balance: ${final_account['balance']:.2f}"
        )

    def run_forever(self):

        self.running = True

        print("Trading AI Paper Monitor started.")
        print("MODE: PAPER TRADING ONLY")
        print(f"ACCOUNT ID: {self.account_id}")
        print(f"SYMBOLS: {self.symbols}")
        print(f"INTERVAL: {self.interval}")
        print(f"CYCLE: {self.cycle_seconds}s")

        while self.running:

            try:

                self.run_cycle()

            except KeyboardInterrupt:

                self.running = False
                print("\nMonitor stopped.")

            except Exception as exc:

                print(
                    f"\nCycle error: {exc}"
                )

            if self.running:
                time.sleep(
                    self.cycle_seconds
                )

    def stop(self):
        self.running = False
