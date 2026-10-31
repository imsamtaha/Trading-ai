"""Read-only evidence audit for ATLAS Paper Council decisions.

Input: JSONL records with decision_id, timestamp, votes, risk, outcome.
No broker imports, no writes to input, no order execution.
"""
import argparse
import json
from collections import Counter
from pathlib import Path


def audit(records):
    findings = []
    ids = []
    for line_no, row in enumerate(records, 1):
        if not isinstance(row, dict):
            findings.append({"line": line_no, "gate": "schema", "status": "FAIL"})
            continue
        key = row.get("decision_id")
        if not key:
            findings.append({"line": line_no, "gate": "decision_id", "status": "FAIL"})
        else:
            ids.append(key)
        for field in ("timestamp", "votes", "risk", "outcome"):
            if field not in row or row[field] is None:
                findings.append({"line": line_no, "gate": field, "status": "UNVERIFIED"})
        risk = row.get("risk")
        outcome = row.get("outcome")
        if isinstance(risk, dict) and risk.get("veto") is True:
            if isinstance(outcome, dict) and outcome.get("opened") is True:
                findings.append({"line": line_no, "gate": "risk_veto", "status": "FAIL"})
        votes = row.get("votes")
        if isinstance(votes, list):
            for vote in votes:
                if not isinstance(vote, dict) or not all(
                    vote.get(k) is not None for k in ("agent", "direction", "timestamp", "reason")
                ):
                    findings.append({"line": line_no, "gate": "vote_provenance", "status": "UNVERIFIED"})
                    break
    duplicates = sorted(str(k) for k, n in Counter(ids).items() if n > 1)
    if duplicates:
        findings.append({"gate": "unique_decisions", "status": "FAIL", "ids": duplicates})
    statuses = Counter(f["status"] for f in findings)
    return {
        "records": len(records),
        "status": "FAIL" if statuses["FAIL"] else ("UNVERIFIED" if statuses["UNVERIFIED"] else "PASS"),
        "findings": findings,
        "note": "Schema-level audit only; does not establish profitability, OOS validity, or live runtime state.",
        "execution_mode": "READ_ONLY_PAPER_EVIDENCE",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("journal", type=Path)
    parser.add_argument("--output", type=Path, help="Optional report path; never overwrites input")
    args = parser.parse_args()
    try:
        rows = [json.loads(line) for line in args.journal.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, ValueError) as exc:
        parser.error(f"Unable to read valid JSONL: {exc}")
    result = audit(rows)
    report = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        if args.output.resolve() == args.journal.resolve():
            parser.error("Report cannot overwrite input journal")
        args.output.write_text(report + "\n", encoding="utf-8")
    else:
        print(report)
    return 1 if result["status"] == "FAIL" else 2 if result["status"] == "UNVERIFIED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
