"""ATLAS Operations Manager: one-shot, PAPER-only health gate over an exported journal.

Does not attach to MT5, place orders, start trading, update settings, or claim
runtime verification. Intended for periodic read-only invocation by an operator.
"""
import argparse
import json
import os
from pathlib import Path

from scripts.audit_paper_evidence import audit


def assess(records, live_flag):
    evidence = audit(records)
    live_is_off = isinstance(live_flag, str) and live_flag.strip().lower() == "false"
    if live_is_off:
        environment_gate = "PASS"
    elif live_flag is None:
        environment_gate = "UNVERIFIED"
    else:
        environment_gate = "FAIL"

    blocked = evidence["status"] != "PASS" or environment_gate != "PASS"
    actions = []
    if environment_gate != "PASS":
        actions.append("Verify ATLAS_LIVE_TRADING=false in the actual runtime; do not switch live on.")
    if evidence["status"] != "PASS":
        actions.append("Investigate evidence findings and verify the export schema against real Council journals.")
    actions.append("Confirm CI, Windows/MT5 runtime, agent-vote-to-outcome joins and OOS evidence separately before merge.")
    return {
        "role": "ATLAS_OPERATIONS_MANAGER",
        "mode": "READ_ONLY_PAPER",
        "operations_status": "BLOCKED" if blocked else "PAPER_SCHEMA_CHECK_ONLY",
        "gates": {"paper_evidence": evidence["status"], "live_disabled_environment_flag": environment_gate},
        "audit": evidence,
        "runtime_verified": False,
        "auto_remediation_executed": False,
        "actions": actions,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("journal", type=Path, help="Private JSONL export to inspect without modifying")
    args = parser.parse_args(argv)
    try:
        records = [json.loads(line) for line in args.journal.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, ValueError) as exc:
        parser.error(f"Unable to read exported PAPER journal: {exc}")
    report = assess(records, os.getenv("ATLAS_LIVE_TRADING"))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["operations_status"] == "PAPER_SCHEMA_CHECK_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
