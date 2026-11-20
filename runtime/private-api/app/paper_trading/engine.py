from app.database.repository import (
    create_position,
    close_position,
    get_open_positions,
    get_account,
)


class PersistentPaperTradingEngine:

    def __init__(self, account_id: int):
        self.account_id = account_id

    def account(self):
        account = get_account(self.account_id)

        if not account:
            raise ValueError("Paper account not found.")

        return account

    def open_position(
        self,
        symbol,
        direction,
        entry,
        stop_loss,
        take_profit,
        position_size,
    ):
        if direction not in {"LONG", "SHORT"}:
            raise ValueError(
                "Direction must be LONG or SHORT."
            )

        if position_size <= 0:
            raise ValueError(
                "Position size must be greater than zero."
            )

        position_id = create_position(
            account_id=self.account_id,
            symbol=symbol,
            direction=direction,
            entry=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
        )

        return {
            "position_id": position_id,
            "account_id": self.account_id,
            "symbol": symbol,
            "direction": direction,
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "position_size": position_size,
            "status": "OPEN",
        }

    def close_position(
        self,
        position_id,
        exit_price,
        reason="MANUAL",
    ):
        positions = get_open_positions(self.account_id)

        position = next(
            (
                p for p in positions
                if p["id"] == position_id
            ),
            None,
        )

        if not position:
            raise ValueError(
                "Open position not found."
            )

        if position["direction"] == "LONG":
            pnl = (
                exit_price - position["entry"]
            ) * position["position_size"]
        else:
            pnl = (
                position["entry"] - exit_price
            ) * position["position_size"]

        trade_id = close_position(
            position_id=position_id,
            exit_price=exit_price,
            pnl=pnl,
            reason=reason,
        )

        return {
            "trade_id": trade_id,
            "position_id": position_id,
            "symbol": position["symbol"],
            "direction": position["direction"],
            "entry": position["entry"],
            "exit": exit_price,
            "pnl": pnl,
            "reason": reason,
            "status": "CLOSED",
        }

    def positions(self):
        return get_open_positions(
            self.account_id
        )

    def calculate_equity(self, market_prices):
        account = self.account()
        positions = self.positions()

        unrealized_pnl = 0.0
        exposure = 0.0
        position_details = []

        for position in positions:

            symbol = position["symbol"]
            current_price = market_prices.get(symbol)

            if current_price is None:
                continue

            entry = position["entry"]
            size = position["position_size"]

            if position["direction"] == "LONG":
                pnl = (current_price - entry) * size
            else:
                pnl = (entry - current_price) * size

            position_value = current_price * size

            unrealized_pnl += pnl
            exposure += position_value

            position_details.append({
                "position_id": position["id"],
                "symbol": symbol,
                "direction": position["direction"],
                "entry": entry,
                "current_price": current_price,
                "position_size": size,
                "position_value": position_value,
                "unrealized_pnl": pnl,
            })

        equity = account["balance"] + unrealized_pnl

        return {
            "balance": account["balance"],
            "unrealized_pnl": unrealized_pnl,
            "equity": equity,
            "exposure": exposure,
            "open_positions": len(positions),
            "positions": position_details,
        }
