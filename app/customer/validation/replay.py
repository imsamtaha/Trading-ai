from __future__ import annotations


def replay_snapshots(snapshots, evaluator):
    report = []
    for snapshot in snapshots:
        decision = evaluator(snapshot)
        report.append({
            "snapshot_id": snapshot.snapshot_id,
            "customer_id": snapshot.customer_id,
            "account_id": snapshot.account_id,
            "mode": snapshot.mode.value,
            "decision": decision.decision.value,
            "confidence": round(float(decision.confidence), 6),
            "rationale": tuple(decision.rationale),
            "blockers": tuple(decision.blockers),
        })
    return report
