"""Read-only Bigdata research ingestion boundary for ATLAS.

Accepts externally retrieved, cited research records. No broker adapter, network
credentials, model training or order execution is included.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def normalize_research_record(record: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    """Normalize one sourced research item; fail closed on missing provenance."""
    if not isinstance(record, dict):
        raise ValueError("research record must be a dictionary")
    title = str(record.get("title") or "").strip()
    url = str(record.get("url") or "").strip()
    published = str(record.get("timestamp") or "").strip()
    if not title or not url.startswith("https://") or not published:
        raise ValueError("title, HTTPS source URL and publication timestamp required")
    try:
        stamp = datetime.fromisoformat(published.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid publication timestamp") from exc
    if stamp.tzinfo is None:
        raise ValueError("publication timestamp must include timezone")
    current = now or datetime.now(timezone.utc)
    age = (current - stamp).total_seconds()
    if age < -300:
        raise ValueError("publication timestamp is in the future")
    return {
        "provider": "bigdata",
        "title": title,
        "source_url": url,
        "published_at": stamp.astimezone(timezone.utc).isoformat(),
        "retrieved_at": current.astimezone(timezone.utc).isoformat(),
        "age_seconds": max(0, int(age)),
        "stale": age > 24 * 3600,
        "asset": str(record.get("asset") or "UNSPECIFIED").strip().upper(),
        "summary": str(record.get("summary") or "").strip(),
        "research_only": True,
        "paper_only": True,
        "broker_execution_allowed": False,
        "signal_action": "HOLD",
    }


def normalize_research_batch(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize provider search results without converting news into trade signals."""
    if not isinstance(records, list):
        raise ValueError("records must be a list")
    return [normalize_research_record(record) for record in records]
