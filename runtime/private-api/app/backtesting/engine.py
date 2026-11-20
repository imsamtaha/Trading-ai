from dataclasses import dataclass


@dataclass
class BacktestTrade:
    symbol: str
    direction: str
    entry: float
    exit: float
    stop_loss: float
    take_profit: float
    position_size: float
    pnl: float
    reason: str
    entry_index: int
    exit_index: int


class BacktestEngine:

    def __init__(
        self,
        initial_balance=10000.0,
        risk_per_trade=0.01,
    ):
        self.initial_balance = float(
            initial_balance
        )

        self.balance = float(
            initial_balance
        )

        self.risk_per_trade = float(
            risk_per_trade
        )

        self.trades = []
        self.equity_curve = []

    def calculate_position_size(
        self,
        entry,
        stop_loss,
    ):

        risk_amount = (
            self.balance
            * self.risk_per_trade
        )

        stop_distance = abs(
            entry - stop_loss
        )

        if stop_distance <= 0:
            return 0.0

        return (
            risk_amount
            / stop_distance
        )

    def calculate_pnl(
        self,
        direction,
        entry,
        exit_price,
        position_size,
    ):

        if direction == "LONG":

            return (
                exit_price - entry
            ) * position_size

        if direction == "SHORT":

            return (
                entry - exit_price
            ) * position_size

        raise ValueError(
            "Direction must be LONG or SHORT."
        )

    def check_exit(
        self,
        direction,
        candle,
        stop_loss,
        take_profit,
    ):

        high = float(candle["high"])
        low = float(candle["low"])

        if direction == "LONG":

            if low <= stop_loss:
                return (
                    stop_loss,
                    "STOP_LOSS",
                )

            if high >= take_profit:
                return (
                    take_profit,
                    "TAKE_PROFIT",
                )

        elif direction == "SHORT":

            if high >= stop_loss:
                return (
                    stop_loss,
                    "STOP_LOSS",
                )

            if low <= take_profit:
                return (
                    take_profit,
                    "TAKE_PROFIT",
                )

        return None, None

    def run(
        self,
        symbol,
        candles,
        signal_function,
        minimum_history=50,
    ):

        if len(candles) <= minimum_history:
            raise ValueError(
                "Not enough candles for backtesting."
            )

        open_trade = None

        self.trades = []
        self.equity_curve = []

        for index in range(
            minimum_history,
            len(candles),
        ):

            candle = candles[index]

            # -----------------------------------------
            # Manage existing position FIRST
            # -----------------------------------------

            if open_trade is not None:

                exit_price, reason = (
                    self.check_exit(
                        open_trade["direction"],
                        candle,
                        open_trade["stop_loss"],
                        open_trade["take_profit"],
                    )
                )

                if exit_price is not None:

                    pnl = self.calculate_pnl(
                        open_trade["direction"],
                        open_trade["entry"],
                        exit_price,
                        open_trade["position_size"],
                    )

                    self.balance += pnl

                    trade = BacktestTrade(
                        symbol=symbol,
                        direction=open_trade[
                            "direction"
                        ],
                        entry=open_trade["entry"],
                        exit=exit_price,
                        stop_loss=open_trade[
                            "stop_loss"
                        ],
                        take_profit=open_trade[
                            "take_profit"
                        ],
                        position_size=open_trade[
                            "position_size"
                        ],
                        pnl=pnl,
                        reason=reason,
                        entry_index=open_trade[
                            "entry_index"
                        ],
                        exit_index=index,
                    )

                    self.trades.append(
                        trade
                    )

                    open_trade = None

            # -----------------------------------------
            # Generate NEW signal
            #
            # Only candles BEFORE the current candle
            # are supplied to the strategy.
            # -----------------------------------------

            if open_trade is None:

                historical_candles = candles[
                    :index
                ]

                signal = signal_function(
                    historical_candles
                )

                if not signal:
                    self.equity_curve.append(
                        self.balance
                    )
                    continue

                direction = signal.get(
                    "direction"
                )

                entry = float(
                    signal.get(
                        "entry",
                        candle["open"],
                    )
                )

                stop_loss = float(
                    signal["stop_loss"]
                )

                take_profit = float(
                    signal["take_profit"]
                )

                if direction not in {
                    "LONG",
                    "SHORT",
                }:
                    self.equity_curve.append(
                        self.balance
                    )
                    continue

                position_size = (
                    self.calculate_position_size(
                        entry,
                        stop_loss,
                    )
                )

                if position_size <= 0:
                    self.equity_curve.append(
                        self.balance
                    )
                    continue

                open_trade = {
                    "direction": direction,
                    "entry": entry,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "position_size": position_size,
                    "entry_index": index,
                }

            self.equity_curve.append(
                self.balance
            )

        # ---------------------------------------------
        # Close an unfinished trade at final close
        # ---------------------------------------------

        if open_trade is not None:

            final_candle = candles[-1]

            exit_price = float(
                final_candle["close"]
            )

            pnl = self.calculate_pnl(
                open_trade["direction"],
                open_trade["entry"],
                exit_price,
                open_trade["position_size"],
            )

            self.balance += pnl

            self.trades.append(
                BacktestTrade(
                    symbol=symbol,
                    direction=open_trade[
                        "direction"
                    ],
                    entry=open_trade["entry"],
                    exit=exit_price,
                    stop_loss=open_trade[
                        "stop_loss"
                    ],
                    take_profit=open_trade[
                        "take_profit"
                    ],
                    position_size=open_trade[
                        "position_size"
                    ],
                    pnl=pnl,
                    reason="END_OF_TEST",
                    entry_index=open_trade[
                        "entry_index"
                    ],
                    exit_index=len(candles) - 1,
                )
            )

        return self.results()

    def results(self):

        total_trades = len(
            self.trades
        )

        wins = [
            trade
            for trade in self.trades
            if trade.pnl > 0
        ]

        losses = [
            trade
            for trade in self.trades
            if trade.pnl < 0
        ]

        net_pnl = sum(
            trade.pnl
            for trade in self.trades
        )

        gross_profit = sum(
            trade.pnl
            for trade in wins
        )

        gross_loss = abs(
            sum(
                trade.pnl
                for trade in losses
            )
        )

        if total_trades:
            win_rate = (
                len(wins)
                / total_trades
                * 100
            )
        else:
            win_rate = 0.0

        if gross_loss > 0:
            profit_factor = (
                gross_profit
                / gross_loss
            )
        else:
            profit_factor = (
                "INF"
                if gross_profit > 0
                else 0.0
            )

        equity = (
            self.initial_balance
        )

        peak = equity
        max_drawdown = 0.0

        for trade in self.trades:

            equity += trade.pnl

            peak = max(
                peak,
                equity,
            )

            drawdown = (
                peak - equity
            )

            max_drawdown = max(
                max_drawdown,
                drawdown,
            )

        return {
            "initial_balance": round(
                self.initial_balance,
                2,
            ),
            "final_balance": round(
                self.balance,
                2,
            ),
            "net_pnl": round(
                net_pnl,
                2,
            ),
            "return_percent": round(
                (
                    net_pnl
                    / self.initial_balance
                    * 100
                ),
                2,
            ),
            "total_trades": total_trades,
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate": round(
                win_rate,
                2,
            ),
            "profit_factor": (
                profit_factor
                if isinstance(
                    profit_factor,
                    str,
                )
                else round(
                    profit_factor,
                    2,
                )
            ),
            "max_drawdown": round(
                max_drawdown,
                2,
            ),
            "trades": [
                trade.__dict__
                for trade in self.trades
            ],
        }
