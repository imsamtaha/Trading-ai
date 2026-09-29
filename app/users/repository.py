from __future__ import annotations

import os
from copy import deepcopy
from typing import Any

import requests



class UserRepositoryError(RuntimeError):
    pass


class MemoryUserRepository:
    def __init__(self) -> None:
        self.profiles: dict[str, dict[str, Any]] = {}
        self.settings: dict[str, dict[str, Any]] = {}
        self.subscriptions: dict[str, dict[str, Any]] = {}
        self.mt5_connections: dict[str, dict[str, Any]] = {}
        self.executive_events: dict[str, list[dict[str, Any]]] = {}
        self.execution_guard_events: dict[str, list[dict[str, Any]]] = {}
        self.execution_guard_drafts: dict[tuple[str, str], dict[str, Any]] = {}

    def get_or_create_profile(self, user_id: str, email: str | None = None) -> dict[str, Any]:
        if user_id not in self.profiles:
            self.profiles[user_id] = {"user_id": user_id, "email": email, "display_name": None}
            self.settings[user_id] = {"user_id": user_id, "language": "en", "theme": "dark"}
            self.subscriptions[user_id] = {"user_id": user_id, "plan": "FREE", "status": "ACTIVE"}
        elif email and not self.profiles[user_id].get("email"):
            self.profiles[user_id]["email"] = email
        return deepcopy(self.profiles[user_id])

    def get_user_settings(self, user_id: str) -> dict[str, Any]:
        self.get_or_create_profile(user_id)
        return deepcopy(self.settings[user_id])

    def update_user_settings(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.get_or_create_profile(user_id)
        allowed = {key: payload[key] for key in ("language", "theme") if key in payload}
        self.settings[user_id].update(allowed)
        return deepcopy(self.settings[user_id])

    def get_subscription(self, user_id: str) -> dict[str, Any]:
        self.get_or_create_profile(user_id)
        return deepcopy(self.subscriptions[user_id])

    def get_mt5_connection(self, user_id: str) -> dict[str, Any] | None:
        value = self.mt5_connections.get(user_id)
        return deepcopy(value) if value else None

    def set_mt5_connection(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.get_or_create_profile(user_id)
        row = {"user_id": user_id, **payload}
        self.mt5_connections[user_id] = row
        return deepcopy(row)

    def clear_mt5_connection(self, user_id: str) -> None:
        self.mt5_connections.pop(user_id, None)

    def add_executive_event(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.get_or_create_profile(user_id)
        row = {"user_id": user_id, **payload}
        self.executive_events.setdefault(user_id, []).append(row)
        return deepcopy(row)

    def list_executive_events(self, user_id: str) -> list[dict[str, Any]]:
        return deepcopy(self.executive_events.get(user_id, []))

    def add_execution_guard_event(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.get_or_create_profile(user_id)
        row = {"user_id": user_id, **payload}
        self.execution_guard_events.setdefault(user_id, []).append(row)
        return deepcopy(row)

    def list_execution_guard_events(self, user_id: str) -> list[dict[str, Any]]:
        return deepcopy(self.execution_guard_events.get(user_id, []))

    def save_trade_draft(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        key = (user_id, str(payload["draft_id"]))
        if key in self.execution_guard_drafts:
            raise ValueError("Duplicate trade draft")
        row = {"user_id": user_id, **payload}
        self.execution_guard_drafts[key] = row
        return deepcopy(row)

    def get_trade_draft(self, user_id: str, draft_id: str) -> dict[str, Any] | None:
        row = self.execution_guard_drafts.get((user_id, draft_id))
        return deepcopy(row) if row else None

    def mark_trade_draft(self, user_id: str, draft_id: str, status: str) -> dict[str, Any] | None:
        row = self.execution_guard_drafts.get((user_id, draft_id))
        if row is None:
            return None
        row["status"] = status
        return deepcopy(row)


class SupabaseUserRepository:
    def __init__(self) -> None:
        from app.auth.supabase_auth import supabase_publishable_key

        self.base_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.publishable_key = supabase_publishable_key()
        if not self.base_url or not self.publishable_key:
            raise UserRepositoryError("Supabase user persistence is not configured.")

    def _headers(self, prefer: str = "return=representation") -> dict[str, str]:
        from app.auth.supabase_auth import current_access_token

        return {
            "apikey": self.publishable_key,
            "Authorization": f"Bearer {current_access_token()}",
            "Content-Type": "application/json",
            "Prefer": prefer,
        }

    def _select_one(self, table: str, user_id: str) -> dict[str, Any] | None:
        response = requests.get(
            f"{self.base_url}/rest/v1/{table}",
            headers=self._headers(),
            params={"user_id": f"eq.{user_id}", "limit": "1"},
            timeout=10,
        )
        if not response.ok:
            raise UserRepositoryError(f"Supabase read failed for {table}.")
        data = response.json()
        return data[0] if isinstance(data, list) and data else None

    def _upsert(self, table: str, row: dict[str, Any]) -> dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/rest/v1/{table}",
            headers=self._headers("resolution=merge-duplicates,return=representation"),
            json=row,
            timeout=10,
        )
        if not response.ok:
            raise UserRepositoryError(f"Supabase write failed for {table}.")
        data = response.json()
        return data[0] if isinstance(data, list) and data else row

    def get_or_create_profile(self, user_id: str, email: str | None = None) -> dict[str, Any]:
        profile = self._select_one("atlas_user_profiles", user_id)
        if profile is None:
            profile = self._upsert("atlas_user_profiles", {"user_id": user_id, "email": email})
            self._upsert("atlas_user_settings", {"user_id": user_id, "language": "en", "theme": "dark"})
        return profile

    def get_user_settings(self, user_id: str) -> dict[str, Any]:
        self.get_or_create_profile(user_id)
        return self._select_one("atlas_user_settings", user_id) or {"user_id": user_id, "language": "en", "theme": "dark"}

    def update_user_settings(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.get_or_create_profile(user_id)
        allowed = {key: payload[key] for key in ("language", "theme") if key in payload}
        return self._upsert("atlas_user_settings", {"user_id": user_id, **allowed})

    def get_subscription(self, user_id: str) -> dict[str, Any]:
        self.get_or_create_profile(user_id)
        return self._select_one("atlas_user_subscriptions", user_id) or {"user_id": user_id, "plan": "FREE", "status": "ACTIVE", "billing_reference": None, "expires_at": None}

    def get_mt5_connection(self, user_id: str) -> dict[str, Any] | None:
        return self._select_one("atlas_user_mt5_demo_connections", user_id)

    def set_mt5_connection(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._upsert("atlas_user_mt5_demo_connections", {"user_id": user_id, **payload})

    def clear_mt5_connection(self, user_id: str) -> None:
        response = requests.delete(
            f"{self.base_url}/rest/v1/atlas_user_mt5_demo_connections",
            headers=self._headers("return=minimal"),
            params={"user_id": f"eq.{user_id}"},
            timeout=10,
        )
        if not response.ok:
            raise UserRepositoryError("Supabase delete failed for atlas_user_mt5_demo_connections.")

    def add_executive_event(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        row = {"user_id": user_id, **payload}
        response = requests.post(
            f"{self.base_url}/rest/v1/demo_executive_events",
            headers=self._headers("return=representation"),
            json=row,
            timeout=10,
        )
        if not response.ok:
            raise UserRepositoryError("Supabase insert failed for demo_executive_events.")
        data = response.json()
        return data[0] if isinstance(data, list) and data else row

    def list_executive_events(self, user_id: str) -> list[dict[str, Any]]:
        response = requests.get(
            f"{self.base_url}/rest/v1/demo_executive_events",
            headers=self._headers(),
            params={"user_id": f"eq.{user_id}", "order": "created_at.desc", "limit": "100"},
            timeout=10,
        )
        if not response.ok:
            raise UserRepositoryError("Supabase read failed for demo_executive_events.")
        data = response.json()
        return data if isinstance(data, list) else []

    def add_execution_guard_event(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        row={"user_id": user_id, **payload}
        r=requests.post(f"{self.base_url}/rest/v1/execution_guard_events", headers=self._headers("return=representation"), json=row, timeout=10)
        if not r.ok: raise UserRepositoryError("Supabase insert failed for execution_guard_events.")
        data=r.json(); return data[0] if isinstance(data,list) and data else row

    def list_execution_guard_events(self, user_id: str) -> list[dict[str, Any]]:
        r=requests.get(f"{self.base_url}/rest/v1/execution_guard_events", headers=self._headers(), params={"user_id":f"eq.{user_id}","order":"created_at.desc","limit":"100"}, timeout=10)
        if not r.ok: raise UserRepositoryError("Supabase read failed for execution_guard_events.")
        data=r.json(); return data if isinstance(data,list) else []

    def save_trade_draft(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        row={"draft_id": payload["draft_id"], "user_id": user_id, "decision_id": payload["decision_id"],
             "status": payload["status"], "expires_at": payload["expires_at"], "payload": payload}
        r=requests.post(f"{self.base_url}/rest/v1/execution_guard_drafts", headers=self._headers("return=representation"), json=row, timeout=10)
        if not r.ok: raise UserRepositoryError("Supabase insert failed for execution_guard_drafts.")
        return payload

    def get_trade_draft(self, user_id: str, draft_id: str) -> dict[str, Any] | None:
        r=requests.get(f"{self.base_url}/rest/v1/execution_guard_drafts", headers=self._headers(), params={"user_id":f"eq.{user_id}","draft_id":f"eq.{draft_id}","limit":"1"}, timeout=10)
        if not r.ok: raise UserRepositoryError("Supabase read failed for execution_guard_drafts.")
        data=r.json(); row=data[0] if isinstance(data,list) and data else None
        if not row: return None
        payload=dict(row.get("payload") or {}); payload["status"]=row.get("status", payload.get("status"))
        return payload

    def mark_trade_draft(self, user_id: str, draft_id: str, status: str) -> dict[str, Any] | None:
        response = requests.patch(
            f"{self.base_url}/rest/v1/execution_guard_drafts",
            headers=self._headers("return=representation"),
            params={"user_id": f"eq.{user_id}", "draft_id": f"eq.{draft_id}"},
            json={"status": status}, timeout=10,
        )
        if not response.ok:
            raise UserRepositoryError("Supabase update failed for execution_guard_drafts.")
        data = response.json()
        return data[0] if isinstance(data, list) and data else None
