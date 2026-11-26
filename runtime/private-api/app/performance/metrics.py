from math import sqrt


def calculate_metrics(trades, initial_balance=10000.0):

    if not trades:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "net_pnl": 0.0,
            "average_win": 0.0,
            "average_loss": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
            "max_drawdown": 0.0,
            "max_drawdown_percent": 0.0,
            "return_percent": 0.0,
        }

    pnls = [
        float(trade["pnl"])
        for trade in trades
    ]

    total_trades = len(pnls)

    wins = [
        pnl for pnl in pnls
        if pnl > 0
    ]

    losses = [
        pnl for pnl in pnls
        if pnl < 0
    ]

    winning_trades = len(wins)
    losing_trades = len(losses)

    net_pnl = sum(pnls)

    win_rate = (
        winning_trades / total_trades * 100
    )

    average_win = (
        sum(wins) / len(wins)
        if wins
        else 0.0
    )

    average_loss = (
        abs(sum(losses) / len(losses))
        if losses
        else 0.0
    )

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    if gross_loss > 0:
        profit_factor = (
            gross_profit / gross_loss
        )
    else:
        profit_factor = float("inf") if gross_profit else 0.0

    expectancy = (
        net_pnl / total_trades
    )

    # Equity curve
    equity = initial_balance
    peak_equity = initial_balance
    max_drawdown = 0.0

    for pnl in pnls:

        equity += pnl

        if equity > peak_equity:
            peak_equity = equity

        drawdown = peak_equity - equity

        if drawdown > max_drawdown:
            max_drawdown = drawdown

    max_drawdown_percent = (
        max_drawdown / peak_equity * 100
        if peak_equity > 0
        else 0.0
    )

    return_percent = (
        net_pnl / initial_balance * 100
        if initial_balance > 0
        else 0.0
    )

    return {
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": round(win_rate, 2),
        "net_pnl": round(net_pnl, 2),
        "average_win": round(average_win, 2),
        "average_loss": round(average_loss, 2),
        "profit_factor": (
            round(profit_factor, 2)
            if profit_factor != float("inf")
            else "INF"
        ),
        "expectancy": round(expectancy, 2),
        "max_drawdown": round(max_drawdown, 2),
        "max_drawdown_percent": round(
            max_drawdown_percent,
            2,
        ),
        "return_percent": round(
            return_percent,
            2,
        ),
    }
