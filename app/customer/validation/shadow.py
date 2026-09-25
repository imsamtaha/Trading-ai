from __future__ import annotations


def run_shadow(snapshot, evaluator):
    decision = evaluator(snapshot)
    return {
        "snapshot_id": snapshot.snapshot_id,
        "customer_id": snapshot.customer_id,
        "account_id": snapshot.account_id,
        "mode": snapshot.mode.value,
        "decision": decision.decision.value,
        "confidence": decision.confidence,
        "executed": False,
    }
