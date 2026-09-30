from __future__ import annotations

from typing import Any

from .models import ExecutionRequest


class DemoExecutor:
    """Executes an already-approved DEMO request against the MT5 service."""

    def __init__(self, mt5_service: Any) -> None:
        self.mt5_service = mt5_service

    def execute(self, user_id: str, request: ExecutionRequest) -> dict[str, Any]:
        payload = request.model_dump(mode="json")
        payload["confirmed"] = True
        return self.mt5_service.place_manual_order(user_id, payload)
