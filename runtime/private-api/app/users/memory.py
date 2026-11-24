"""Persistent per-user memory for ATLAS AI."""
from __future__ import annotations

import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def _db_path() -> Path:
    configured = os.getenv("ATLAS_MEMORY_DB", "").strip()
    if configured:
        return Path(configured)
    root = Path(os.getenv(
        "ATLAS_DATA_DIR",
        r"C:\Users\KHAT W TELEPHONE\ATLAS_Backup",
    ))
    return root / "atlas_memory.sqlite3"


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    _init(db)
    return db
