"""Durable, credential-free audit and replay guard for manual MT5 orders."""
from __future__ import annotations

import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


class TradeAudit:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or os.getenv("ATLAS_TRADE_AUDIT_DB", "data/trade_orders.sqlite3"))

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=10)
        db.execute("""CREATE TABLE IF NOT EXISTS manual_mt5_orders (
            user_id TEXT NOT NULL,
            request_id TEXT NOT NULL,
            account_masked TEXT NOT NULL,
            account_type TEXT NOT NULL,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            volume REAL NOT NULL,
            status TEXT NOT NULL,
            ticket INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (user_id, request_id)
        )""")
        return db

    def reserve(self, user_id: str, request_id: str, account_masked: str,
                account_type: str, symbol: str, direction: str, volume: float) -> bool:
        now = datetime.now(UTC).isoformat()
        with self._connect() as db:
            try:
                db.execute(
                    """INSERT INTO manual_mt5_orders
                    (user_id, request_id, account_masked, account_type, symbol, direction,
                     volume, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?)""",
                    (user_id, request_id, account_masked, account_type, symbol, direction, volume, now, now),
                )
            except sqlite3.IntegrityError:
                return False
        return True

    def finish(self, user_id: str, request_id: str, status: str, ticket: int | None = None) -> None:
        with self._connect() as db:
            db.execute(
                "UPDATE manual_mt5_orders SET status=?, ticket=?, updated_at=? WHERE user_id=? AND request_id=?",
                (status, ticket, datetime.now(UTC).isoformat(), user_id, request_id),
            )

    def status(self, user_id: str, request_id: str) -> str | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT status FROM manual_mt5_orders WHERE user_id=? AND request_id=?",
                (user_id, request_id),
            ).fetchone()
        return row[0] if row else None
