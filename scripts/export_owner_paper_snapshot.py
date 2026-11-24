"""Export existing ATLAS Windows PAPER records to a signed, read-only owner snapshot.

Never sends MT5 orders; never creates trading outcomes, demo metrics or market data.
A signed snapshot authenticates the file; it does not prove strategy performance.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def _strict_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"),
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError("invalid constant " + x)))


def _optional(path: Path):
    if not path.exists():
        return None
    return _strict_json(path)


def _journal(path: Path):
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            if line.strip():
                try:
                    value = json.loads(line)
                except (ValueError, UnicodeError) as exc:
                    raise ValueError(f"Corrupt journal {path.name} line {line_no}") from exc
                if not isinstance(value, dict):
                    raise ValueError(f"Invalid journal row {path.name} line {line_no}")
                rows.append(value)
    return rows


def _training_sessions(rows: list[dict]) -> list[dict]:
    evidence: dict[str, tuple[str, str]] = {}
    now = datetime.now(timezone.utc)
    conflicting = set()
    for row in rows:
        snapshot = row.get("snapshot_id")
        outcome = row.get("realized_direction")
        if not isinstance(snapshot, str) or not snapshot.strip() or outcome not in ("BUY", "SELL", "HOLD"):
            continue
        try:
            time = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
            if time.tzinfo is None or time > now:
                continue
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        day = time.astimezone(timezone.utc).date().isoformat()
        item = (day, outcome)
        if evidence.setdefault(snapshot.strip(), item) != item:
            conflicting.add(snapshot.strip())
    counts = Counter(day for snapshot, (day, _) in evidence.items() if snapshot not in conflicting)
    return [{"date_utc": day, "settled_examples": count, "source": "PAPER_COUNCIL_JOURNAL"}
            for day, count in sorted(counts.items(), reverse=True)]


def _shadow_review(root: Path) -> tuple[dict, list[dict]]:
    path = root / os.getenv("ATLAS_SKLEARN_SHADOW_REPORT", "data/council-agent-scores.json")
    try:
        report = _optional(path) if path.stat().st_size <= 2 * 1024 * 1024 else None
    except (OSError, ValueError):
        report = None
    if (not isinstance(report, dict) or report.get("training_environment") != "PAPER_RESEARCH_ONLY"
            or report.get("source_kind") != "SETTLED_PAPER_COUNCIL_JOURNAL"
            or any(report.get(key) is not False for key in (
                "broker_execution_allowed", "active_council_weights_changed", "live_trading_enabled"))):
        return {"status": "UNAVAILABLE"}, []
    fields = ("status", "generated_at", "unique_snapshots", "min_samples_per_agent", "freshness_gate_passed", "mlflow_run_id")
    summary = {key: report[key] for key in fields if key in report}
    agents = report.get("agents")
    if not isinstance(agents, dict):
        return summary, []
    rows = []
    for agent, row in sorted(agents.items()):
        if not isinstance(row, dict):
            continue
        metrics = row.get("metrics")
        metrics = metrics if isinstance(metrics, dict) else {}
        rows.append({"agent": agent, "status": row.get("status"), "samples": row.get("samples"),
                     "candidate_weight": row.get("candidate_weight"), **{
                         key: metrics.get(key) for key in ("holdout_examples", "oos_accuracy", "baseline_oos_accuracy", "oos_brier", "ece")}})
    return summary, rows


def collect(root: Path) -> dict:
    status = _optional(root / os.getenv("ATLAS_DEMO_STATUS", "data/atlas_demo_status.json"))
    ledger = _optional(root / os.getenv("ATLAS_DEMO_LEDGER", "data/atlas_demo_ledger.json"))
    profile = _optional(root / os.getenv("ATLAS_COUNCIL_PROFILE", "data/atlas_council_profile.json"))
    if not isinstance(status, dict) or not isinstance(ledger, dict):
        raise ValueError("Windows worker status and PAPER ledger must both exist and be valid.")
    if (status.get("live_execution") is not False or status.get("mode") != "LIVE_DEMO"):
        raise ValueError("Worker is not confirmed PAPER-only by the saved status.")
    trades = ledger.get("closed_trades", [])
    opens = ledger.get("open_positions", [])
    if not isinstance(trades, list) or not isinstance(opens, list):
        raise ValueError("Invalid PAPER ledger collections")
    stamped = status.get("updated_at")
    if not isinstance(stamped, str) or datetime.fromisoformat(stamped.replace("Z", "+00:00")).tzinfo is None:
        raise ValueError("Worker heartbeat missing timezone")
    training = _journal(root / os.getenv("ATLAS_COUNCIL_TRAINING_JOURNAL", "data/atlas_council_training.jsonl"))
    training = [x for x in training if x.get("execution_environment") == "PAPER"
                and x.get("broker_execution_allowed") is False]
    if profile is not None and (not isinstance(profile, dict)
                               or profile.get("training_environment") != "PAPER"
                               or profile.get("broker_execution_allowed") is not False):
        raise ValueError("Council profile lacks PAPER provenance")
    agents = []
    info = (profile or {}).get("agents", {})
    if not isinstance(info, dict):
        raise ValueError("Invalid agent profile")
    opinions = {}
    for item in training:
        for op in item.get("opinions", []):
            if isinstance(op, dict) and isinstance(op.get("agent"), str):
                opinions[op["agent"]] = op
    for name, entry in info.items():
        if not isinstance(name, str) or not isinstance(entry, dict):
            continue
        opinion = opinions.get(name, {})
        agents.append({"agent": name, "weight": entry.get("weight"),
                       "confidence": opinion.get("confidence"),
                       "decision": opinion.get("decision"),
                       "source": "council_profile_and_paper_training"})
    history = []
    for trade in [*trades, *opens]:
        if not isinstance(trade, dict) or not isinstance(trade.get("id"), str):
            raise ValueError("Invalid trade identity in ledger")
        if trade.get("broker_execution_allowed", False) is not False:
            continue
        history.append({"trade_id": trade["id"], "opened_at": trade.get("opened_at"),
                        "closed_at": trade.get("closed_at"), "symbol": trade.get("symbol"),
                        "direction": trade.get("direction"), "status": trade.get("status"),
                        "result_r": trade.get("r_multiple"), "source": "mt5_demo_paper_ledger"})
    decisions = []
    for trade in trades:
        decision = trade.get("decision")
        if not isinstance(decision, dict):
            continue
        if decision.get("broker_execution_allowed") is not False:
            continue
        decisions.append({"decision_id": decision.get("decision_id"),
                          "snapshot_id": decision.get("snapshot_id"),
                          "symbol": trade.get("symbol"),
                          "decision": decision.get("decision"),
                          "outcome": trade.get("exit_reason"),
                          "provenance": "paper_ledger"})
    signals = []
    for item in _journal(root / os.getenv("ATLAS_SIGNAL_JOURNAL", "data/atlas_signals.jsonl")):
        if item.get("execution_environment") != "PAPER" or item.get("broker_execution_allowed") is not False:
            continue
        signals.append({"id": item.get("decision_id"), "timestamp": item.get("timestamp"),
                        "symbol": item.get("symbol"), "decision": item.get("decision"),
                        "confidence": item.get("confidence"), "risk_gate": item.get("risk_gate"),
                        "evidence_id": item.get("snapshot_id"), "status": item.get("status")})
    research, evaluations = _shadow_review(root)
    snapshot = {
        "data_origin": "WINDOWS_PAPER", "source_environment": "PAPER",
        "broker_execution_allowed": False, "as_of": stamped,
        "source_id": "paper-status-" + hashlib.sha256(status["updated_at"].encode()).hexdigest()[:12],
        "data": {
            "council_agents": agents, "mt5_demo": {"status": status.get("status"),
              "account_type": "DEMO_REPORTED", "timestamp": stamped},
            "signals": signals[-500:], "risk_controls": {},
            "training_progress": {"sample_count": len(training),
                                  "training_profile_version": (profile or {}).get("version")},
            "decision_evidence": decisions[-500:], "paper_trade_history": list(reversed(history)),
            "training_sessions": _training_sessions(training),
            "sklearn_research": research, "sklearn_evaluations": evaluations,
            "windows_runtime": {"status": status.get("status"), "heartbeat": stamped,
                                "cycle_seconds": status.get("cycle_seconds")},
            "shadow_learning": {"status": "PAPER_ONLY" if profile else "UNAVAILABLE",
                 "samples": len(training), "training_examples": len(training),
                 "updated_at": (profile or {}).get("generated_at"),
                 "agent_weights": {k: v.get("weight") for k, v in info.items() if isinstance(v, dict)}},
        },
    }
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Existing Windows ATLAS checkout")
    parser.add_argument("--output", default="data/atlas_owner_snapshot.json")
    args = parser.parse_args()
    if os.getenv("ATLAS_LIVE_TRADING", "false").lower() != "false":
        raise SystemExit("Refusing export when live trading is not explicitly disabled")
    key = os.getenv("ATLAS_OWNER_SNAPSHOT_HMAC_KEY", "")
    if len(key) < 32:
        raise SystemExit("ATLAS_OWNER_SNAPSHOT_HMAC_KEY must contain at least 32 characters")
    raw = collect(Path(args.root))
    canonical = json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    raw["signature"] = hmac.new(key.encode(), canonical.encode(), hashlib.sha256).hexdigest()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(raw, ensure_ascii=False, allow_nan=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    print(json.dumps({"status": "EXPORTED_PAPER_ONLY", "path": str(path),
                      "worker_as_of": raw["as_of"], "paper_trades": len(raw["data"]["paper_trade_history"]),
                      "live_orders_sent": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
