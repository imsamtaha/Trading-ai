from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote

import requests


class CustomerRepositoryError(RuntimeError):
    pass


class SupabaseCustomerAccountRepository:
    TABLE = "atlas_customer_accounts"

    def __init__(self, base_url: str, service_key: str):
        self.base_url = base_url.rstrip("/")
        self.service_key = service_key

    @classmethod
    def from_env(cls):
        base_url = os.getenv("SUPABASE_URL", "").strip()
        service_key = (os.getenv("SUPABASE_SECRET_KEY", "").strip()
                       or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip())
        return cls(base_url, service_key) if base_url and service_key else None

    def _headers(self, prefer: str | None = None) -> dict[str, str]:
        headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def upsert_account(self, row: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/rest/v1/{self.TABLE}?on_conflict=customer_id,account_id"
        response = requests.post(url, headers=self._headers("resolution=merge-duplicates,return=representation"), json=row, timeout=10)
        if not response.ok:
            raise CustomerRepositoryError(f"customer account upsert failed ({response.status_code})")
        data = response.json()
        return dict(data[0]) if isinstance(data, list) and data else dict(row)

    def get_account(self, customer_id: str, account_id: str) -> dict[str, Any] | None:
        query = f"customer_id=eq.{quote(customer_id)}&account_id=eq.{quote(account_id)}&select=*"
        response = requests.get(f"{self.base_url}/rest/v1/{self.TABLE}?{query}", headers=self._headers(), timeout=10)
        if not response.ok:
            raise CustomerRepositoryError(f"customer account lookup failed ({response.status_code})")
        rows = response.json()
        return dict(rows[0]) if isinstance(rows, list) and rows else None

    def list_accounts_by_subject(self, auth_subject: str) -> list[dict[str, Any]]:
        query = f"auth_subject=eq.{quote(auth_subject)}&select=customer_id,account_id,tier,mode,broker,broker_login,broker_server&order=created_at.asc"
        response = requests.get(f"{self.base_url}/rest/v1/{self.TABLE}?{query}", headers=self._headers(), timeout=10)
        if not response.ok:
            raise CustomerRepositoryError(f"customer account list failed ({response.status_code})")
        rows = response.json()
        return [dict(row) for row in rows] if isinstance(rows, list) else []
