from __future__ import annotations

from typing import Any, Callable

from app.runtime_control.service import get_demo_execution_enabled
from .models import ExecutionRequest


class DemoExecutionDisabled(RuntimeError):
    pass


class DemoExecutor:
    """Executes an already-approved DEMO request against the MT5 service."""

    def __init__(self, mt5_service: Any, *, execution_enabled: Callable[[], bool] | None = None) -> None:
        self.mt5_service = mt5_service
        self.execution_enabled = execution_enabled or get_demo_execution_enabled

    def execute(self, user_id: str, request: ExecutionRequest) -> dict[str, Any]:
        if request.account_type != "DEMO" or not self.execution_enabled():
            raise DemoExecutionDisabled("Demo execution is disabled by the ATLAS runtime switch.")
        payload = request.model_dump(mode="json")
        payload["confirmed"] = True
        return self.mt5_service.place_manual_order(user_id, payload)
