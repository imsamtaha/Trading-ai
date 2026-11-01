"""Read-only compatibility gate for historical ATLAS Council PAPER training JSONL.

Historical 'opinions' are NOT equivalent to decision vote provenance, and
'realized_direction' is NOT an independently verified order outcome.
Never manufacture a decision_id, risk veto, opening status, reason or timestamp.
"""
import argparse
import json
import math
from collections import Counter
from pathlib import Path

from scripts.audit_paper_evidence import audit as audit_decisions


def _text(v):
    return isinstance(v, str) and bool(v.strip())


def inspect_legacy(records, canonical_decisions=None):
    findings = []
    snapshot_ids = []
    snapshots = {}
    for line, row in enumerate(records, 1):
        if not isinstance(row, dict):
            findings.append({"line": line, "gate": "legacy_schema", "status": "FAIL"})
            continue

        sid = row.get("snapshot_id")
        if not _text(sid):
            findings.append({"line": line, "gate": "snapshot_id", "status": "FAIL"})
        else:
            sid = sid.strip()
            snapshot_ids.append(sid)
            snapshots.setdefault(sid, row)

        if not _text(row.get("timestamp")):
            findings.append({"line": line, "gate": "timestamp", "status": "UNVERIFIED"})
        if row.get("broker_execution_allowed") is not False:
            findings.append({
                "line": line, "gate": "broker_execution_allowed",
                "status": "FAIL" if row.get("broker_execution_allowed") is True else "UNVERIFIED",
            })
        if not _text(row.get("execution_environment")) or row["execution_environment"].strip().lower() not in ("paper", "demo", "shadow"):
            findings.append({"line": line, "gate": "execution_environment", "status": "UNVERIFIED"})
        opinions = row.get("opinions")
        if not isinstance(opinions, list) or not opinions:
            findings.append({"line": line, "gate": "opinions", "status": "UNVERIFIED"})
        else:
            names = []
            for opinion in opinions:
                if not isinstance(opinion, dict) or not _text(opinion.get("agent")) or not _text(opinion.get("decision")):
                    findings.append({"line": line, "gate": "opinion_identity", "status": "UNVERIFIED"})
                    break
                name = opinion["agent"].strip().lower()
                names.append(name)
                confidence = opinion.get("confidence")
                if isinstance(confidence, bool) or not isinstance(confidence, (float, int)) or not math.isfinite(confidence):
                    findings.append({"line": line, "gate": "opinion_confidence", "status": "UNVERIFIED"})
                    break
            if len(names) != len(set(names)):
                findings.append({"line": line, "gate": "duplicate_opinion_agent", "status": "UNVERIFIED"})
        if row.get("realized_direction") is None:
            findings.append({"line": line, "gate": "realized_direction", "status": "UNVERIFIED"})

    duplicates = sorted(k for k, n in Counter(snapshot_ids).items() if n > 1)
    if duplicates:
        findings.append({"gate": "duplicate_snapshot_id", "status": "FAIL", "count": len(duplicates)})
    if not records:
        findings.append({"gate": "empty_legacy_journal", "status": "UNVERIFIED"})

    joined = 0
    canonical_count = None
    if canonical_decisions is None:
        findings.append({"gate": "canonical_decision_outcome_source", "status": "UNVERIFIED"})
    else:
        canonical_count = len(canonical_decisions)
        canonical = audit_decisions(canonical_decisions)
        if canonical["status"] != "PASS":
            findings.append({"gate": "canonical_decision_schema", "status": canonical["status"]})
        for row in canonical_decisions:
            if not isinstance(row, dict) or not _text(row.get("source_snapshot_id")):
                findings.append({"gate": "source_snapshot_id", "status": "UNVERIFIED"})
                continue
            sid = row["source_snapshot_id"].strip()
            source = snapshots.get(sid)
            if source is None:
                findings.append({"gate": "missing_source_snapshot", "status": "UNVERIFIED"})
                continue
            source_votes = {
                (x["agent"].strip().casefold(), x["decision"].strip().casefold())
                for x in source.get("opinions", [])
                if isinstance(x, dict) and _text(x.get("agent")) and _text(x.get("decision"))
            } if isinstance(source.get("opinions"), list) else set()
            decision_votes = {
                (x["agent"].strip().casefold(), x["direction"].strip().casefold())
                for x in row.get("votes", [])
                if isinstance(x, dict) and _text(x.get("agent")) and _text(x.get("direction"))
            } if isinstance(row.get("votes"), list) else set()
            if not source_votes or source_votes != decision_votes:
                findings.append({"gate": "source_vote_mismatch", "status": "UNVERIFIED"})
                continue
            joined += 1
        if not canonical_decisions or joined != len(canonical_decisions):
            findings.append({"gate": "decision_to_snapshot_coverage", "status": "UNVERIFIED"})
        if len(set(snapshot_ids)) != joined:
            findings.append({"gate": "snapshot_to_decision_coverage", "status": "UNVERIFIED"})

    # The legacy journal never contains independent veto/open/outcome evidence.
    # Only a separately validated canonical decision source can clear this gate.
    states = Counter(x["status"] for x in findings)
    return {
        "status": "FAIL" if states["FAIL"] else ("UNVERIFIED" if states["UNVERIFIED"] else "PASS"),
        "mode": "READ_ONLY_PAPER_EVIDENCE",
        "legacy_records": len(records),
        "canonical_decisions": canonical_count,
        "verified_joins": joined,
        "findings": findings,
        "broker_write_executed": False,
        "note": "A schema PASS is not proof of actual execution, profitability, fresh runtime, or live safety.",
    }


def _load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("legacy_journal", type=Path)
    p.add_argument("--canonical-decisions", type=Path, help="Optional independently sourced decision/veto/outcome JSONL")
    args = p.parse_args(argv)
    try:
        legacy = _load_jsonl(args.legacy_journal)
        decisions = _load_jsonl(args.canonical_decisions) if args.canonical_decisions else None
    except (OSError, ValueError) as exc:
        p.error(f"Cannot read valid private JSONL: {exc}")
    result = inspect_legacy(legacy, decisions)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return {"PASS": 0, "FAIL": 1, "UNVERIFIED": 2}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
