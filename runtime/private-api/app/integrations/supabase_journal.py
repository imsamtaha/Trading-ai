from __future__ import annotations

import os
from typing import Any

import requests


class SupabaseJournalError(RuntimeError):
    pass


class SupabaseSignalJournal:
    """Persist ATLAS dry-run analysis records through the Supabase REST API.

    Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in the local runtime.
    The service-role credential must never be committed to source control.
    """

    def __init__(self) -> None:
        self.base_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not self.base_url or not self.service_role_key:
            raise SupabaseJournalError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for Supabase persistence."
            )

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def record_analysis(
        self,
        *,
        symbol: str,
        server: str,
        login: int,
        equity: float,
        decision: dict[str, Any],
        timeframe: str = "MTF",
        reason: str | None = None,
    ) -> dict[str, Any]:
        row = {
            "symbol": symbol,
            "timeframe": timeframe,
            "decision": decision.get("decision", "WAIT"),
            "confidence": decision.get("execution_confidence", decision.get("confidence")),
            "risk_level": decision.get("risk_level"),
            "directional_score": decision.get("directional_score"),
            "status": "DRY_RUN",
            "reason": reason or "ATLAS deterministic analysis cycle",
            "payload": {
                "server": server,
                "login": login,
                "equity": equity,
                "decision": decision,
            },
        }

        url = f"{self.base_url}/rest/v1/atlas_execution_events"
        response = requests.post(
            url,
            headers=self._headers(),
            json=row,
            timeout=15,
        )
        if not response.ok:
            raise SupabaseJournalError(
                f"Supabase insert failed ({response.status_code}): {response.text[:500]}"
            )
        data = response.json()
        return data[0] if isinstance(data, list) and data else row
