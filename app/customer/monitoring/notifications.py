def build_notification(snapshot, *, trace_id: str, event: str, payload: dict) -> dict:
    return {
        "customer_id": snapshot.customer_id,
        "account_id": snapshot.account_id,
        "mode": snapshot.mode.value,
        "snapshot_id": snapshot.snapshot_id,
        "trace_id": trace_id,
        "event": event,
        "payload": dict(payload),
    }
