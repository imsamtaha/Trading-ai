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
WEB = Path(__file__).resolve().parent / "owner_ui" / "index.html"

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
    "release_validation": ("pr_103_status", "pr_103_test_status", "issue_82_status", "ledger_readback", "windows_verified", "ci_status", "source", "as_of"),
}
METRIC_KEYS = {"oos_accuracy", "ece", "samples", "win_rate", "profit_factor",
               "expectancy_r", "max_drawdown_pct", "agent_agreement", "agent_conflict"}


def owner_only(credentials: HTTPBasicCredentials | None = Depends(security)) -> None:
    user = os.getenv("ATLAS_OWNER_DASHBOARD_USER", "").strip()
    password = os.getenv("ATLAS_OWNER_DASHBOARD_PASSWORD", "")
    if (os.getenv("ATLAS_DASHBOARD_ONLY", "false").strip().lower() != "true"
            or os.getenv("ATLAS_LIVE_TRADING", "false").strip().lower() != "false"):
        raise HTTPException(503, "Owner dashboard requires PAPER read-only mode")
    if not user or len(password) < 16:
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
        "data": {**projected, "audit_flags": audit_paper_rows(projected),
                 "release_readiness": release_readiness(projected, status, audit_paper_rows(projected))},
    }


def audit_paper_rows(data: dict[str, Any]) -> list[dict[str, str]]:
    """Conservative read-only evidence checks. Never interpret absence as a successful audit."""
    flags: list[dict[str, str]] = []
    seen: set[str] = set()
    decisions = data.get("decision_evidence", [])
    for index, row in enumerate(decisions):
        ident = row.get("decision_id")
        ref = str(ident or f"row-{index + 1}")
        def flag(code: str, detail: str) -> None:
            flags.append({"code": code, "reference": ref, "detail": detail,
                          "source": "signed_paper_decision_evidence"})
        if not ident:
            flag("MISSING_DECISION_ID", "decision_id absent")
        elif ident in seen:
            flag("DUPLICATE_DECISION_ID", "decision_id occurs more than once")
        else:
            seen.add(ident)
        if not row.get("snapshot_id"):
            flag("MISSING_PROVENANCE", "snapshot_id absent")
        if not row.get("outcome"):
            flag("MISSING_OUTCOME", "settled outcome absent")
        if not row.get("council_votes"):
            flag("MISSING_VOTES", "Council votes unavailable")
        veto = row.get("risk_veto")
        action = str(row.get("decision") or "").upper()
        if veto is True and action in {"BUY", "SELL", "OPEN"}:
            flag("RISK_VETO_ACTION_CONFLICT", "action conflicts with risk veto")
    return flags[:500]


def release_readiness(data: dict[str, Any], evidence_status: str,
                      flags: list[dict[str, str]]) -> dict[str, Any]:
    """Fail closed: source authentication is not operational sign-off."""
    validation = data.get("release_validation", {})
    checks = {
        "signed_snapshot_fresh": evidence_status == "VERIFIED",
        "decision_audit_clean": bool(data.get("decision_evidence")) and not flags,
        "windows_verified": validation.get("windows_verified") is True,
        "ledger_readback": validation.get("ledger_readback") == "PASS",
        "pr_103_tests": validation.get("pr_103_test_status") == "PASS",
        "ci": validation.get("ci_status") == "PASS",
        "issue_82_closed": validation.get("issue_82_status") == "CLOSED",
    }
    return {"status": "REVIEW_REQUIRED" if all(checks.values()) else "BLOCKED",
            "checks": checks, "source": "derived_from_signed_snapshot",
            "note": "REVIEW_REQUIRED is not authorization to deploy or place orders"}


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
