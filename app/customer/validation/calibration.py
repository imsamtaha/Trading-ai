from __future__ import annotations

import json
from pathlib import Path


class CalibrationBook:
    def __init__(self, path):
        self.path = Path(path)
        self.data = self._load()

    def _load(self):
        if self.path.exists():
            return json.loads(self.path.read_text(encoding="utf-8"))
        return {}

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, sort_keys=True), encoding="utf-8")

    @staticmethod
    def _bucket(confidence: float) -> str:
        pct = max(0, min(99, int(float(confidence) * 100)))
        low = (pct // 10) * 10
        return f"{low:02d}-{low + 9:02d}"

    def record(self, confidence: float, *, success: bool) -> None:
        bucket = self._bucket(confidence)
        row = self.data.setdefault(bucket, {"count": 0, "successes": 0})
        row["count"] += 1
        row["successes"] += int(bool(success))
        self._save()

    def metrics(self) -> dict:
        return {
            key: {
                "count": row["count"],
                "success_rate": (row["successes"] / row["count"]) if row["count"] else 0.0,
            }
            for key, row in self.data.items()
        }
