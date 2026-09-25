from __future__ import annotations


class AuditStore:
    def __init__(self):
        self.events: list[dict] = []

    def append(self, event: dict) -> dict:
        record = dict(event)
        self.events.append(record)
        return record

    def by_trace(self, trace_id: str, *, customer_id: str | None = None) -> list[dict]:
        return [e for e in self.events if e.get("trace_id") == trace_id and (customer_id is None or e.get("customer_id") == customer_id)]
