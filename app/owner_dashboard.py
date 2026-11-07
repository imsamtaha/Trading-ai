"""Private owner-only read surface for attested Windows PAPER evidence.

No broker adapters, order-write functions, or mutating routes are imported here.
Unknown, missing, unsigned and stale data never becomes live-performance evidence.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

router = APIRouter(prefix="/sam", tags=["owner"])
security = HTTPBasic(auto_error=False)
WEB = Path(__file__).resolve().parents[1] / "web" / "sam" / "index.html"

TABLE_KEYS = {
    "council_agents": ("agent", "decision", "confidence", "calibrated_confidence", "weight", "conflict_score", "updated_at", "source"),
    "signals": ("id", "timestamp", "symbol", "decision", "confidence", "risk_gate", "evidence_id", "status"),
    "decision_evidence": ("decision_id", "timestamp", "symbol", "snapshot_id", "decision", "risk_veto", "outcome", "provenance", "conflict_score", "council_votes"),
    "paper_trade_history": ("trade_id", "opened_at", "closed_at", "symbol", "direction", "status", "result_r", "evidence_id", "source"),
}
OBJECT_KEYS = {
    "mt5_demo": ("status", "account_type", "broker", "server", "login_masked", "timestamp"),
    "risk_controls": ("daily_loss_limit_pct", "max_open_risk_pct", "max_positions", "margin_level_min_pct", "daily_loss_actual_pct", "veto_count", "status"),
    "training_progress": ("before", "after", "sample_count", "training_profile_version", "candidate_status", "as_of"),
    "windows_runtime": ("status", "heartbeat", "cycle_seconds", "last_error", "service", "process_count"),
    "shadow_learning": ("status", "samples", "latest_outcome", "updated_at", "training_examples", "drift", "before", "after", "agent_weights"),
}
METRIC_KEYS = {"oos_accuracy", "ece", "samples", "win_rate", "profit_factor",
               "expectancy_r", "max_drawdown_pct", "agent_agreement", "agent_conflict"}


def owner_only(credentials: HTTPBasicCredentials | None = Depends(security)) -> None:
    user = os.getenv("ATLAS_OWNER_DASHBOARD_USER", "").strip()
    password = os.getenv("ATLAS_OWNER_DASHBOARD_PASSWORD", "")
    if not user or not password:
        raise HTTPException(503, "Owner authentication is not configured")
    valid = (credentials is not None
             and secrets.compare_digest(credentials.username.encode('utf-8'), user.encode('utf-8'))
             and secrets.compare_digest(credentials.password.encode('utf-8'), password.encode('utf-8')))
    if not valid:
        raise HTTPException(401, "Owner only", headers={"WWW-Authenticate": 'Basic realm="ATLAS Owner"'})


def _missing(reason: str, status: str = "UNAVAILABLE") -> dict[str, Any]:
    return {
        "status": status, "reason": reason, "verified": False, "as_of": None, "source_id": None,
        "source_environment": "PAPER",
        "safeguards": {"live_trading_enabled": False, "real_money_orders_allowed": False,
                       "broker_execution": "READ_ONLY"},
        "data": {**{key: [] for key in TABLE_KEYS}, **{key: {} for key in OBJECT_KEYS}},
    }


def _allowed(row: Any, keys: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {}
    cleaned = {}
    for key in keys:
        if key not in row:
            continue
        value = row[key]
        if isinstance(value, (str, int, float, bool)) or value is None:
            if isinstance(value, float) and not math.isfinite(value):
                continue
            cleaned[key] = value
        elif key in {"before", "after"} and isinstance(value, dict):
            cleaned[key] = {k: float(v) for k, v in value.items()
                            if k in METRIC_KEYS and isinstance(v, (float, int))
                            and not isinstance(v, bool) and math.isfinite(v)}
        elif key == "agent_weights" and isinstance(value, dict):
            cleaned[key] = {k[:80]: float(v) for k, v in list(value.items())[:40]
                            if isinstance(k, str) and isinstance(v, (int, float))
                            and not isinstance(v, bool) and math.isfinite(v)}
        elif key == "council_votes" and isinstance(value, list):
            cleaned[key] = [_allowed(v, ("agent", "decision", "confidence")) for v in value[:40]]
    return cleaned


def read_evidence() -> dict[str, Any]:
    location = os.getenv("ATLAS_OWNER_SNAPSHOT_PATH", "").strip()
    signing_key = os.getenv("ATLAS_OWNER_SNAPSHOT_HMAC_KEY", "")
    if not location or len(signing_key) < 32:
        return _missing("SNAPSHOT_OR_SIGNATURE_KEY_NOT_CONFIGURED")
    try:
        path = Path(location).expanduser().resolve(strict=True)
        if not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
            return _missing("SNAPSHOT_MISSING_OR_OVERSIZED")
        with path.open(encoding="utf-8") as source:
            raw = json.load(source, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("non-finite")))
    except (OSError, ValueError, TypeError, UnicodeError):
        return _missing("SNAPSHOT_UNREADABLE")
    if not isinstance(raw, dict):
        return _missing("SNAPSHOT_INVALID", "UNVERIFIED")
    signature = raw.get("signature")
    if not isinstance(signature, str) or len(signature) != 64:
        return _missing("SIGNATURE_MISSING", "UNVERIFIED")
    unsigned = {k: v for k, v in raw.items() if k != "signature"}
    canonical = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    expected = hmac.new(signing_key.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return _missing("INVALID_SIGNATURE", "UNVERIFIED")
    if (raw.get("source_environment") != "PAPER"
            or raw.get("data_origin") != "WINDOWS_PAPER"
            or raw.get("broker_execution_allowed") is not False
            or not isinstance(raw.get("source_id"), str) or not raw["source_id"].strip()):
        return _missing("INVALID_PAPER_PROVENANCE", "UNVERIFIED")
    try:
        stamped = datetime.fromisoformat(raw["as_of"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        if stamped.tzinfo is None or stamped > now + timedelta(minutes=5):
            raise ValueError("timestamp is not valid")
    except (KeyError, TypeError, AttributeError, ValueError):
        return _missing("INVALID_TIMESTAMP", "UNVERIFIED")
    source = raw.get("data")
    if not isinstance(source, dict):
        return _missing("DATA_INVALID", "UNVERIFIED")
    projected = {}
    for section, keys in TABLE_KEYS.items():
        values = source.get(section, [])
        if not isinstance(values, list):
            return _missing("INVALID_TABLE_" + section, "UNVERIFIED")
        projected[section] = [_allowed(item, keys) for item in values[:500]]
    for section, keys in OBJECT_KEYS.items():
        value = source.get(section, {})
        if not isinstance(value, dict):
            return _missing("INVALID_OBJECT_" + section, "UNVERIFIED")
        projected[section] = _allowed(value, keys)
    status = "STALE" if now - stamped > timedelta(hours=6) else "VERIFIED"
    return {
        "status": status, "reason": "EVIDENCE_OLDER_THAN_6_HOURS" if status == "STALE" else None,
        "verified": True, "as_of": stamped.isoformat(), "source_id": raw["source_id"],
        "source_environment": "PAPER",
        "safeguards": {"live_trading_enabled": False, "real_money_orders_allowed": False,
                       "broker_execution": "READ_ONLY"},
        "data": projected,
    }


@router.get("", include_in_schema=False)
@router.get("/", include_in_schema=False)
def owner_dashboard(_: None = Depends(owner_only)):
    return FileResponse(WEB, media_type="text/html",
                        headers={"Cache-Control": "no-store", "X-Frame-Options": "DENY",
                                 "X-Content-Type-Options": "nosniff"})


@router.get("/api/snapshot", include_in_schema=False)
def owner_snapshot(_: None = Depends(owner_only)):
    return JSONResponse(read_evidence(), headers={"Cache-Control": "no-store",
                                                   "X-Content-Type-Options": "nosniff"})
