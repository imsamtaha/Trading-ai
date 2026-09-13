from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn


def _reject_non_json_constant(value: str) -> NoReturn:
    raise ValueError(f"Invalid JSON numeric constant: {value}")


class SignalJournal:
    """Append-only JSONL journal for ATLAS analysis cycles.

    The journal is deliberately local and provider-neutral. It does not require
    Supabase credentials and never places orders.
    """

    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path or os.getenv("ATLAS_SIGNAL_JOURNAL", "data/atlas_signals.jsonl"))

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **record,
        }
        encoded = json.dumps(
            payload,
            allow_nan=False,
            default=str,
            separators=(",", ":"),
        ) + "\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        return payload

    def verify(self) -> dict[str, object]:
        records = 0
        malformed_lines: list[int] = []

        if not self.path.exists():
            return {
                "status": "MISSING",
                "records": 0,
                "malformed_records": 0,
                "malformed_lines": [],
            }

        with self.path.open("rb") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                if not raw_line.strip():
                    continue
                try:
                    record = json.loads(
                        raw_line.decode("utf-8"),
                        parse_constant=_reject_non_json_constant,
                    )
                except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                    malformed_lines.append(line_number)
                    continue
                if not isinstance(record, dict):
                    malformed_lines.append(line_number)
                    continue
                records += 1

        return {
            "status": "CORRUPT" if malformed_lines else "OK",
            "records": records,
            "malformed_records": len(malformed_lines),
            "malformed_lines": malformed_lines,
        }

    def count(self) -> int:
        if not self.path.exists():
            return 0
        with self.path.open("r", encoding="utf-8") as handle:
            return sum(1 for _ in handle)
