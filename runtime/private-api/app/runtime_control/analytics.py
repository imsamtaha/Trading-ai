from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

_LOCK = Lock()
_PROCESS_STARTED_AT = datetime.now(timezone.utc)


def process_started_at() -> str:
    return _PROCESS_STARTED_AT.isoformat()


def uptime_seconds() -> int:
    return max(0, int((datetime.now(timezone.utc) - _PROCESS_STARTED_AT).total_seconds()))


def _path() -> Path:
    configured = os.getenv("ATLAS_ANALYTICS_STATE_FILE", "").strip()
    if configured:
        return Path(configured)
    return Path(os.getenv("TEMP", ".")) / "atlas_runtime_analytics.json"


def _empty() -> dict:
    return {
        "page_views": 0,
        "unique_visitors": [],
        "authenticated_traders": [],
        "sign_ins": 0,
        "sign_outs": 0,
        "last_sign_in_at": None,
        "last_sign_out_at": None,
        "last_visit_at": None,
    }


def _load() -> dict:
    try:
        raw = json.loads(_path().read_text(encoding="utf-8"))
        data = _empty()
        data.update(raw if isinstance(raw, dict) else {})
        return data
    except (OSError, ValueError, TypeError):
        return _empty()


def _save(data: dict) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def new_visitor_id() -> str:
    return uuid4().hex


def _stable_user_id(user_id: str) -> str:
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:24]


def record_visit(visitor_id: str) -> None:
    visitor_id = visitor_id.strip()
    if not visitor_id:
        return
    now = datetime.now(timezone.utc).isoformat()
    with _LOCK:
        data = _load()
        data["page_views"] = int(data.get("page_views", 0)) + 1
        visitors = set(data.get("unique_visitors") or [])
        visitors.add(visitor_id)
        data["unique_visitors"] = sorted(visitors)
        data["last_visit_at"] = now
        _save(data)


def record_sign_in(user_id: str, is_owner: bool) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _LOCK:
        data = _load()
        data["sign_ins"] = int(data.get("sign_ins", 0)) + 1
        if not is_owner:
            traders = set(data.get("authenticated_traders") or [])
            traders.add(_stable_user_id(user_id))
            data["authenticated_traders"] = sorted(traders)
        data["last_sign_in_at"] = now
        _save(data)


def record_sign_out() -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _LOCK:
        data = _load()
        data["sign_outs"] = int(data.get("sign_outs", 0)) + 1
        data["last_sign_out_at"] = now
        _save(data)


def snapshot() -> dict[str, object]:
    with _LOCK:
        data = _load()
    return {
        "page_views": int(data.get("page_views", 0)),
        "unique_visitors": len(data.get("unique_visitors") or []),
        "authenticated_traders": len(data.get("authenticated_traders") or []),
        "sign_ins": int(data.get("sign_ins", 0)),
        "sign_outs": int(data.get("sign_outs", 0)),
        "last_visit_at": data.get("last_visit_at"),
        "last_sign_in_at": data.get("last_sign_in_at"),
        "last_sign_out_at": data.get("last_sign_out_at"),
    }
