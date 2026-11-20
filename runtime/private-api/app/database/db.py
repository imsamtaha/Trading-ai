import sqlite3
from pathlib import Path


DB_PATH = Path("trading_ai.db")


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    connection = get_connection()

    cursor = connection.cursor()

    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS paper_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            initial_balance REAL NOT NULL,
            balance REAL NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry REAL NOT NULL,
            stop_loss REAL NOT NULL,
            take_profit REAL NOT NULL,
            position_size REAL NOT NULL,
            position_value REAL NOT NULL,
            opened_at TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY(account_id)
                REFERENCES paper_accounts(id)
        );

        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            position_id INTEGER,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry REAL NOT NULL,
            exit REAL NOT NULL,
            position_size REAL NOT NULL,
            pnl REAL NOT NULL,
            reason TEXT,
            opened_at TEXT NOT NULL,
            closed_at TEXT NOT NULL,
            FOREIGN KEY(account_id)
                REFERENCES paper_accounts(id)
        );

        CREATE TABLE IF NOT EXISTS trade_journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_id INTEGER,
            market_regime TEXT,
            strategy TEXT,
            confidence REAL,
            thesis TEXT,
            lesson TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(trade_id)
                REFERENCES trades(id)
        );

        CREATE TABLE IF NOT EXISTS performance_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            win_rate REAL,
            profit_factor REAL,
            expectancy REAL,
            max_drawdown REAL,
            total_trades INTEGER,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(account_id)
                REFERENCES paper_accounts(id)
        );
        """
    )

    connection.commit()
    connection.close()


if __name__ == "__main__":
    initialize_database()
    print(f"Database initialized: {DB_PATH}")
