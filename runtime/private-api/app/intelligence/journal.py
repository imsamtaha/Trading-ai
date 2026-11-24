from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SignalJournal:
    """Append-only JSONL journal for ATLAS analysis cycles.

    The journal is deliberately local and provider-neutral. It does not require
    Supabase credentials and never places orders.
    """

    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path or os.getenv("ATLAS_SIGNAL_JOURNAL", "data/atlas_signals.jsonl"))
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **record,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, default=str, separators=(",", ":")) + "\n")
        return payload

    def count(self) -> int:
        if not self.path.exists():
            return 0
        with self.path.open("r", encoding="utf-8") as handle:
            return sum(1 for _ in handle)
