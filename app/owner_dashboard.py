"""Private, read-only ATLAS owner surface. No broker execution imports."""
from __future__ import annotations

import base64
import binascii
import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

router = APIRouter(tags=["owner"])
_UI = Path(__file__).resolve().parent / "owner_ui"
_EXPORT_NAMES = (
    "overview", "agents", "signals", "risk", "training", "decisions",
    "paper_trades", "shadow_learning", "runtime", "mt5_demo",
)
_LIST_KEYS = {"agents", "signals", "decisions", "paper_trades", "shadow_learning"}
_FIELDS = {
    "overview": {"paper_closed", "paper_open", "verified_decisions", "training_examples",
                 "training_acceptance", "last_cycle_at", "council_confidence",
                 "conflict_rate", "paper_win_rate", "paper_net_r"},
    "agents": {"id", "name", "role", "confidence", "conflict", "vote", "weight",
               "sample_count", "status", "as_of"},
    "signals": {"id", "symbol", "action", "confidence", "risk", "status", "as_of", "source"},
    "risk": {"risk_per_trade_pct", "daily_loss_limit_pct", "max_open_risk_pct",
             "max_positions", "margin_level_floor_pct", "last_veto", "veto_count",
             "gate", "as_of"},
    "training": {"before", "after", "sample_count", "accepted_count", "rejected_count",
                 "run_id", "status", "as_of"},
    "decisions": {"id", "decision_id", "symbol", "action", "confidence", "conflict",
                  "risk_verdict", "outcome", "provenance", "as_of", "evidence_id"},
    "paper_trades": {"id", "decision_id", "symbol", "direction", "status", "r_multiple",
                     "opened_at", "closed_at", "outcome", "source"},
    "shadow_learning": {"id", "agent", "decision_id", "lesson", "sample_count",
                        "old_weight", "new_weight", "status", "as_of"},
    "runtime": {"host", "status", "monitor", "heartbeat_at", "last_save_at",
                "read_write_check", "paper_monitor", "last_error", "as_of"},
    "mt5_demo": {"connection", "account_type", "broker", "server", "last_seen_at",
                 "telemetry_status", "trade_allowed", "as_of"},
}

def _owner_auth(request: Request) -> None:
    username = os.getenv("ATLAS_OWNER_DASHBOARD_USERNAME", "sam")
    password = os.getenv("ATLAS_OWNER_DASHBOARD_PASSWORD", "")
    if len(password) < 16:
        raise HTTPException(status_code=503, detail="Owner dashboard credentials are not configured.")
    value = request.headers.get("authorization", "")
    if not value.startswith("Basic "):
        raise HTTPException(status_code=401, detail="Owner authentication required.",
                            headers={"WWW-Authenticate": 'Basic realm="ATLAS Owner"'} )
    try:
        decoded = base64.b64decode(value[6:], validate=True).decode("utf-8")
        supplied_user, supplied_password = decoded.split(":", 1)
    except (ValueError, UnicodeDecodeError, binascii.Error):
        raise HTTPException(status_code=401, detail="Invalid credentials.",
                            headers={"WWW-Authenticate": 'Basic realm="ATLAS Owner"'} ) from None
    if not (secrets.compare_digest(supplied_user, username)
            and secrets.compare_digest(supplied_password, password)):
        raise HTTPException(status_code=401, detail="Invalid credentials.",
                            headers={"WWW-Authenticate": 'Basic realm="ATLAS Owner"'} )

def _headers() -> dict[str, str]:
    return {"Cache-Control": "private, no-store, max-age=0",
            "X-Robots-Tag": "noindex, nofollow, noarchive",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"}

def _read(name: str) -> tuple[Any, dict[str, str]]:
    fallback: Any = [] if name in _LIST_KEYS else {}
    evidence_root = os.getenv("ATLAS_OWNER_EVIDENCE_DIR", "").strip()
    if not evidence_root:
        return fallback, {"status": "UNAVAILABLE", "reason": "Evidence directory not configured"}
    root = Path(evidence_root).expanduser().resolve()
    path = (root / (name + ".json")).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        return fallback, {"status": "UNAVAILABLE", "reason": "No verified export"}
    try:
        if path.stat().st_size > 2_000_000:
            raise ValueError("Export too large")
        doc = json.loads(path.read_text(encoding="utf-8"))
        provenance = doc.get("provenance", {}) if isinstance(doc, dict) else {}
        if (not isinstance(doc, dict) or doc.get("verification") != "VERIFIED"
            or not isinstance(provenance, dict)
            or not all(isinstance(provenance.get(k), str) and provenance[k].strip()
                       for k in ("source", "verified_at", "method"))):
            return fallback, {"status": "UNVERIFIED", "reason": "Missing validated provenance"}
        value = doc.get("data", fallback)
        if name in _LIST_KEYS:
            if not isinstance(value, list):
                raise ValueError("Expected rows")
            value = [
                {k: v for k, v in row.items() if k in _FIELDS[name] and
                 (v is None or isinstance(v, (str, bool, int, float)))}
                for row in value[:500] if isinstance(row, dict)
            ]
        else:
            if not isinstance(value, dict):
                raise ValueError("Expected object")
            value = {k: v for k, v in value.items() if k in _FIELDS[name] and
                     (v is None or isinstance(v, (str, bool, int, float))
                      or (name == "training" and k in ("before", "after") and isinstance(v, dict)))}
            if name == "training":
                for key in ("before", "after"):
                    raw = value.get(key)
                    if isinstance(raw, dict):
                        value[key] = {
                            k: v for k, v in raw.items()
                            if k in {"win_rate", "avg_r", "ece", "brier", "sample_count",
                                     "conflict_rate", "approval_rate"}
                            and (v is None or isinstance(v, (int, float)))
                        }
        return value, {
            "status": "VERIFIED_EXPORT", "source": provenance["source"][:200],
            "verified_at": provenance["verified_at"][:50],
            "method": provenance["method"][:100],
        }
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return fallback, {"status": "UNAVAILABLE", "reason": "Malformed or inaccessible export"}

def _snapshot() -> dict[str, Any]:
    datasets = {}
    evidence = {}
    for key in _EXPORT_NAMES:
        datasets[key], evidence[key] = _read(key)
    return {
        "mode": "PAPER_READ_ONLY", "broker_execution_allowed": False,
        "live_orders_allowed": False,
        "runtime_live_flag_enabled": os.getenv("ATLAS_LIVE_TRADING", "false").lower() == "true",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "datasets": datasets, "evidence": evidence,
    }

@router.get("/sam", include_in_schema=False)
@router.get("/sam/", include_in_schema=False)
def owner_page(request: Request):
    _owner_auth(request)
    return FileResponse(_UI / "index.html", media_type="text/html; charset=utf-8", headers=_headers())

@router.get("/sam/assets/{filename}", include_in_schema=False)
def owner_assets(filename: str, request: Request):
    _owner_auth(request)
    if filename not in ("owner.css", "owner.js"):
        raise HTTPException(status_code=404)
    return FileResponse(_UI / filename, headers=_headers())

@router.get("/sam/api/snapshot", include_in_schema=False)
def owner_snapshot(request: Request):
    _owner_auth(request)
    return JSONResponse(_snapshot(), headers=_headers())
