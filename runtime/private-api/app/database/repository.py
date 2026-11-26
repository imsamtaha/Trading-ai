from datetime import datetime, timezone

from app.database.db import get_connection


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def create_account(
    name: str = "Main Paper Account",
    initial_balance: float = 10000.0,
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO paper_accounts
        (name, initial_balance, balance, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (name, initial_balance, initial_balance, utc_now()),
    )

    connection.commit()
    account_id = cursor.lastrowid
    connection.close()

    return account_id


def get_account(account_id: int):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM paper_accounts
        WHERE id = ?
        """,
        (account_id,),
    )

    account = cursor.fetchone()
    connection.close()

    return dict(account) if account else None


def create_position(
    account_id,
    symbol,
    direction,
    entry,
    stop_loss,
    take_profit,
    position_size,
):
    connection = get_connection()
    cursor = connection.cursor()

    position_value = entry * position_size

    cursor.execute(
        """
        INSERT INTO positions
        (
            account_id,
            symbol,
            direction,
            entry,
            stop_loss,
            take_profit,
            position_size,
            position_value,
            opened_at,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
        """,
        (
            account_id,
            symbol,
            direction,
            entry,
            stop_loss,
            take_profit,
            position_size,
            position_value,
            utc_now(),
        ),
    )

    connection.commit()
    position_id = cursor.lastrowid
    connection.close()

    return position_id


def get_open_positions(account_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM positions
        WHERE account_id = ?
        AND status = 'OPEN'
        ORDER BY id DESC
        """,
        (account_id,),
    )

    positions = [dict(row) for row in cursor.fetchall()]
    connection.close()

    return positions


def close_position(
    position_id,
    exit_price,
    pnl,
    reason,
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM positions
        WHERE id = ?
        """,
        (position_id,),
    )

    position = cursor.fetchone()

    if not position:
        connection.close()
        raise ValueError("Position not found.")

    position = dict(position)

    closed_at = utc_now()

    cursor.execute(
        """
        UPDATE positions
        SET status = 'CLOSED'
        WHERE id = ?
        """,
        (position_id,),
    )

    cursor.execute(
        """
        INSERT INTO trades
        (
            account_id,
            position_id,
            symbol,
            direction,
            entry,
            exit,
            position_size,
            pnl,
            reason,
            opened_at,
            closed_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            position["account_id"],
            position_id,
            position["symbol"],
            position["direction"],
            position["entry"],
            exit_price,
            position["position_size"],
            pnl,
            reason,
            position["opened_at"],
            closed_at,
        ),
    )

    trade_id = cursor.lastrowid

    cursor.execute(
        """
        UPDATE paper_accounts
        SET balance = balance + ?
        WHERE id = ?
        """,
        (pnl, position["account_id"]),
    )

    connection.commit()
    connection.close()

    return trade_id


def get_trades(account_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM trades
        WHERE account_id = ?
        ORDER BY id DESC
        """,
        (account_id,),
    )

    trades = [dict(row) for row in cursor.fetchall()]
    connection.close()

    return trades
