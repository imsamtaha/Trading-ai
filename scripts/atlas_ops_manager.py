"""ATLAS PAPER Operations Manager: read-only evidence gate over private JSONL.

Never connects to MT5, sends orders, changes risk limits or claims live readiness.
Legacy Council opinions require independent canonical decision evidence.
"""
import argparse
import json
import os
from pathlib import Path

from scripts.audit_paper_evidence import audit
from scripts.audit_legacy_council_evidence import inspect_legacy, _load_jsonl


def assess(records, live_flag, journal_format="canonical", canonical_decisions=None):
    if journal_format == "legacy":
        evidence = inspect_legacy(records, canonical_decisions)
    elif journal_format == "canonical":
        evidence = audit(records)
    else:
        raise ValueError("Unsupported journal format")

    live_is_off = isinstance(live_flag, str) and live_flag.strip().lower() == "false"
    environment_gate = "PASS" if live_is_off else ("UNVERIFIED" if live_flag is None else "FAIL")
    blocked = evidence["status"] != "PASS" or environment_gate != "PASS"

    actions = []
    if environment_gate != "PASS":
        actions.append("Verify ATLAS_LIVE_TRADING=false in the actual runtime; do not switch live on.")
    if evidence["status"] != "PASS":
        actions.append("Investigate evidence findings; obtain independent risk veto and actual outcomes without fabricating them.")
    actions.append("Check fresh PAPER heartbeat, immutable journal sources, CI, Windows/MT5 and OOS validation separately before merge.")
    return {
        "role": "ATLAS_OPERATIONS_MANAGER",
        "mode": "READ_ONLY_PAPER",
        "operations_status": "BLOCKED" if blocked else "PAPER_SCHEMA_CHECK_ONLY",
        "gates": {
            "paper_evidence": evidence["status"],
            "live_disabled_environment_flag": environment_gate,
            "runtime_health": "UNVERIFIED",
        },
        "audit": evidence,
        "runtime_verified": False,
        "auto_remediation_executed": False,
        "actions": actions,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("journal", type=Path, help="Private JSONL export to inspect without modifying")
    parser.add_argument("--journal-format", choices=("canonical", "legacy"), default="canonical")
    parser.add_argument("--canonical-decisions", type=Path, help="Independent decision/veto/outcome JSONL for legacy joins")
    args = parser.parse_args(argv)
    if args.canonical_decisions and args.journal_format != "legacy":
        parser.error("--canonical-decisions requires --journal-format legacy")
    try:
        records = _load_jsonl(args.journal)
        canonical = _load_jsonl(args.canonical_decisions) if args.canonical_decisions else None
    except (OSError, ValueError) as exc:
        parser.error(f"Unable to read exported PAPER journal: {exc}")
    report = assess(records, os.getenv("ATLAS_LIVE_TRADING"), args.journal_format, canonical)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["operations_status"] == "PAPER_SCHEMA_CHECK_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
