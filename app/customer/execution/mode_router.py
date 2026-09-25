from __future__ import annotations

from app.customer.contracts import Mode
from app.customer.execution.demo_adapter import DemoAdapter, ExecutionResult


class ModeRouter:
    def __init__(self, demo_adapter: DemoAdapter):
        self.demo_adapter = demo_adapter
        self._by_trace: dict[str, ExecutionResult] = {}

    def execute_demo(self, intent, risk: dict, *, trace_id: str) -> ExecutionResult:
        if trace_id in self._by_trace:
            return self._by_trace[trace_id]
        result = self.demo_adapter.execute(intent, risk, trace_id=trace_id)
        self._by_trace[trace_id] = result
        return result
