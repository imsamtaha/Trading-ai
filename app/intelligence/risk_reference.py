"""Read-only, page-indexed study reference derived from the uploaded risk guide.

This educational index is NOT a risk policy or an execution authorization.
The deterministic Senior Risk engine remains authoritative.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REFERENCE_ID = "atlas-risk-management-tut-v3-20261018"
KNOWLEDGE_FILE = Path(__file__).resolve().parents[2] / "knowledge" / "risk_management_v3.json"


def risk_reference_manifest() -> dict[str, Any]:
    """Safe metadata for Council audit packages, independent of file availability."""
    return {
        "reference_id": REFERENCE_ID,
        "title": "Risk Management tut V3",
        "source_pages": 40,
        "scope": "PAPER_EDUCATION_ONLY",
        "affects_risk_policy": False,
        "broker_execution_allowed": False,
    }


def risk_study_topics() -> list[dict[str, Any]]:
    """Return paraphrased study notes only on explicit education requests."""
    payload = json.loads(KNOWLEDGE_FILE.read_text(encoding="utf-8"))
    if payload.get("reference_id") != REFERENCE_ID:
        raise ValueError("Risk study reference version mismatch")
    return list(payload["topics"])


def risk_study_topic(key: str) -> dict[str, Any] | None:
    lookup = key.strip().lower()
    return next((dict(topic) for topic in risk_study_topics() if topic["key"] == lookup), None)
