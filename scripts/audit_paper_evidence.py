"""Fail-closed, read-only JSONL evidence audit for ATLAS PAPER Council decisions.

Validates the *shape* of evidence only. A PASS does not prove strategy quality,
profitability, order history, correctness of votes, or live runtime safety.
No broker imports or mutations of the journal are performed.
"""
import argparse
import json
from collections import Counter
from pathlib import Path


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def audit(records):
    findings = []
    ids = []
    for line_no, row in enumerate(records, 1):
        if not isinstance(row, dict):
            findings.append({"line": line_no, "gate": "schema", "status": "FAIL"})
            continue

        key = row.get("decision_id")
        if not _text(key):
            findings.append({"line": line_no, "gate": "decision_id", "status": "FAIL"})
        else:
            ids.append(key.strip())

        if not _text(row.get("timestamp")):
            findings.append({"line": line_no, "gate": "timestamp", "status": "UNVERIFIED"})

        votes = row.get("votes")
        if not isinstance(votes, list) or not votes:
            findings.append({"line": line_no, "gate": "votes", "status": "UNVERIFIED"})
        elif any(not isinstance(vote, dict) or not all(
                _text(vote.get(field)) for field in ("agent", "direction", "timestamp", "reason")
            ) for vote in votes):
            findings.append({"line": line_no, "gate": "vote_provenance", "status": "UNVERIFIED"})

        risk = row.get("risk")
        if not isinstance(risk, dict) or type(risk.get("veto")) is not bool:
            findings.append({"line": line_no, "gate": "risk", "status": "UNVERIFIED"})

        outcome = row.get("outcome")
        if not isinstance(outcome, dict) or type(outcome.get("opened")) is not bool:
            findings.append({"line": line_no, "gate": "outcome", "status": "UNVERIFIED"})

        if (isinstance(risk, dict) and risk.get("veto") is True
                and isinstance(outcome, dict) and outcome.get("opened") is True):
            findings.append({"line": line_no, "gate": "risk_veto", "status": "FAIL"})

    duplicates = sorted(key for key, count in Counter(ids).items() if count > 1)
    if duplicates:
        findings.append({"gate": "unique_decisions", "status": "FAIL", "ids": duplicates})
    if not records:
        findings.append({"gate": "nonempty_journal", "status": "UNVERIFIED"})

    statuses = Counter(f["status"] for f in findings)
    return {
        "records": len(records),
        "status": "FAIL" if statuses["FAIL"] else ("UNVERIFIED" if statuses["UNVERIFIED"] else "PASS"),
        "findings": findings,
        "note": "Schema-level evidence only; not proof of provenance truth, outcomes, OOS validity, profitability or runtime safety.",
        "execution_mode": "READ_ONLY_PAPER_EVIDENCE",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("journal", type=Path, help="Private exported JSONL journal; read only")
    parser.add_argument("--output", type=Path, help="Create a new report file; refuses existing files")
    args = parser.parse_args(argv)
    try:
        rows = [json.loads(line) for line in args.journal.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, ValueError) as exc:
        parser.error(f"Unable to read valid JSONL: {exc}")
    result = audit(rows)
    report = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        try:
            # 'x' is exclusive creation. It prevents overwriting the journal,
            # hard links, symlinks and *any* existing file, including reports.
            with args.output.open("x", encoding="utf-8") as destination:
                destination.write(report)
        except OSError as exc:
            parser.error(f"Unable to create a new report (existing files are protected): {exc}")
    else:
        print(report, end="")
    return 1 if result["status"] == "FAIL" else 2 if result["status"] == "UNVERIFIED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
