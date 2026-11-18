"""ATLAS per-agent scikit-learn research on settled PAPER outcomes.

Independent research only. Never imports broker libraries, writes live Council
profiles, sends orders, or promotes champion models. Proposal weights remain
HOLD_BASELINE until a separate reviewed release has validated all gates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.metrics import accuracy_score

from app.intelligence.council_training import CouncilTrainingJournal
from atlas_training.train_agent import calibration_error

MIN_AGENT_SAMPLES = 80
MIN_HOLDOUT_SAMPLES = 20
MIN_OOS_ACCURACY = 0.525
MIN_STABILITY = 0.80
MAX_ECE = 0.10
MIN_BRIER_IMPROVEMENT = 0.01


def _locked(reason: str, n: int = 0) -> dict:
    return {
        "status": "HOLD_BASELINE",
        "samples": n,
        "baseline_weight": 1.0,
        "candidate_weight": None,
        "metrics": {},
        "reasons": [reason],
    }


def _agent_score(rows: list[tuple[float, str, int]], *, min_samples: int) -> dict:
    """Chronological holdout with a one-snapshot embargo, never shuffled."""
    n = len(rows)
    if n < min_samples:
        return _locked(f"insufficient_settled_paper_samples:{n}<{min_samples}", n)
    train_end = int(n * 0.75)
    holdout_start = train_end + 1
    if n - holdout_start < MIN_HOLDOUT_SAMPLES:
        return _locked("insufficient_chronological_holdout", n)
    matrix = np.asarray([
        (confidence, float(direction == "BUY"), float(direction == "SELL"), float(direction == "HOLD"))
        for confidence, direction, correct in rows
    ], dtype=float)
    outcome = np.asarray([correct for confidence, direction, correct in rows], dtype=int)
    x_train, y_train = matrix[:train_end], outcome[:train_end]
    x_test, y_test = matrix[holdout_start:], outcome[holdout_start:]
    if np.unique(y_train).size != 2:
        return _locked("training_outcomes_have_one_class", n)
    model = LogisticRegression(
        C=0.5, max_iter=400, solver="lbfgs", random_state=7
    ).fit(x_train, y_train)
    p_train = model.predict_proba(x_train)[:, 1]
    p_test = model.predict_proba(x_test)[:, 1]
    if not (np.isfinite(p_train).all() and np.isfinite(p_test).all()):
        return _locked("nonfinite_model_probabilities", n)
    pred_train = (p_train >= 0.5).astype(int)
    pred_test = (p_test >= 0.5).astype(int)
    train_acc = float(accuracy_score(y_train, pred_train))
    test_acc = float(accuracy_score(y_test, pred_test))
    baseline_probability = float(np.mean(y_train))
    baseline_oos_accuracy = float(np.mean(y_test == int(baseline_probability >= 0.5)))
    baseline_brier = float(brier_score_loss(y_test, np.full(y_test.size, baseline_probability)))
    test_brier = float(brier_score_loss(y_test, p_test))
    ece = float(calibration_error(p_test, y_test))
    stability = (test_acc / train_acc) if train_acc else 0.0
    brier_improvement = baseline_brier - test_brier

    metrics = {
        "oos_accuracy": round(test_acc, 6),
        "train_accuracy": round(train_acc, 6),
        "stability": round(stability, 6),
        "oos_brier": round(test_brier, 6),
        "baseline_oos_accuracy": round(baseline_oos_accuracy, 6),
        "baseline_brier": round(baseline_brier, 6),
        "brier_improvement": round(brier_improvement, 6),
        "ece": round(ece, 6),
        "train_examples": int(y_train.size),
        "holdout_examples": int(y_test.size),
    }
    reasons = []
    if test_acc < max(MIN_OOS_ACCURACY, baseline_oos_accuracy + 0.005):
        reasons.append("oos_accuracy_below_majority_baseline_or_floor")
    if stability < MIN_STABILITY:
        reasons.append("unstable_relative_to_training")
    if ece > MAX_ECE:
        reasons.append("calibration_error_above_gate")
    if brier_improvement < MIN_BRIER_IMPROVEMENT:
        reasons.append("brier_improvement_below_gate")
    # This is a shadow *proposal* even when gates pass. NEVER update active weights.
    confidence_quality = (0.65 * float(np.mean(y_test))) + (0.35 * (1.0 - test_brier))
    proposal = max(0.5, min(1.5, 0.5 + confidence_quality))
    return {
        "status": "SHADOW_REVIEW" if not reasons else "HOLD_BASELINE",
        "samples": n,
        "baseline_weight": 1.0,
        "candidate_weight": round(proposal, 4) if not reasons else None,
        "metrics": metrics,
        "reasons": reasons,
    }


def evaluate_paper_agents(journal: str | Path, *, min_samples: int = MIN_AGENT_SAMPLES) -> dict:
    """Evaluate each agent independently; reject duplicates and malformed PAPER data."""
    if min_samples < MIN_AGENT_SAMPLES:
        raise ValueError(f"min_samples cannot be reduced below {MIN_AGENT_SAMPLES}")
    source = Path(journal)
    if not source.is_file():
        raise FileNotFoundError(f"settled PAPER journal not found: {source}")
    source_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
    source_timestamp = datetime.fromtimestamp(source.stat().st_mtime, timezone.utc)
    source_age_hours = (datetime.now(timezone.utc) - source_timestamp).total_seconds() / 3600
    freshness_passed = 0 <= source_age_hours <= 48
    entries = CouncilTrainingJournal(str(source)).load()
    seen = set()
    per_agent: dict[str, list[tuple[float, str, int]]] = {}
    for example in entries:
        if example.snapshot_id in seen:
            raise ValueError("duplicate snapshot_id in PAPER journal")
        seen.add(example.snapshot_id)
        for opinion in example.opinions:
            agent = str(opinion.get("agent", "")).strip()
            direction = str(opinion.get("decision", "")).upper()
            if not agent or direction not in ("BUY", "SELL", "HOLD"):
                raise ValueError("invalid agent opinion")
            confidence = float(opinion.get("confidence", float("nan")))
            if not math.isfinite(confidence) or confidence < 0 or confidence > 1:
                raise ValueError("invalid confidence")
            correct = int(direction == example.realized_direction)
            per_agent.setdefault(agent, []).append((confidence, direction, correct))
    agents = {
        agent: _agent_score(rows, min_samples=min_samples)
        for agent, rows in sorted(per_agent.items())
    }
    if not freshness_passed:
        for evaluation in agents.values():
            evaluation["status"] = "HOLD_BASELINE"
            evaluation["candidate_weight"] = None
            evaluation["reasons"].append("stale_or_future_source_timestamp")
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "SHADOW_REVIEW" if any(x["status"] == "SHADOW_REVIEW" for x in agents.values()) else "HOLD_BASELINE",
        "training_environment": "PAPER_RESEARCH_ONLY",
        "source_kind": "SETTLED_PAPER_COUNCIL_JOURNAL",
        "source_sha256": source_sha256,
        "source_last_modified_at": source_timestamp.isoformat(),
        "source_age_hours": round(source_age_hours, 2),
        "freshness_gate_passed": freshness_passed,
        "unique_snapshots": len(seen),
        "min_samples_per_agent": min_samples,
        "reviewers": ["STC-04", "STC-09", "Senior Risk"],
        "agents": agents,
        "broker_execution_allowed": False,
        "active_council_weights_changed": False,
        "council_weight_activation": False,
        "model_registered": False,
        "automatic_promotion": False,
        "live_trading_enabled": False,
    }


def _write_report(path: str | Path, payload: dict) -> Path:
    """Write only to an explicitly provided research file, atomically."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(dir=target.parent, prefix=".sklearn-agent-research-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, allow_nan=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, target)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return target


def log_to_mlflow(payload: dict, *, uri: str) -> str:
    """Log score evidence only, not model artifacts or champion aliases."""
    import mlflow

    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment("ATLAS-PAPER-sklearn-agent-evaluation")
    with mlflow.start_run(run_name="council-agent-shadow-eval", tags={
        "environment": "PAPER_RESEARCH_ONLY",
        "live_trading": "false",
        "council_activation": "false",
        "data_provenance": "settled_paper_journal",
    }) as run:
        mlflow.log_params({
            "min_samples_per_agent": payload["min_samples_per_agent"],
            "unique_snapshots": payload["unique_snapshots"],
            "source_sha256": payload["source_sha256"],
            "governance_status": "HOLD_BASELINE",
        })
        mlflow.log_metrics({
            "total_agents": float(len(payload["agents"])),
            "eligible_shadow_candidates": float(sum(row["status"] == "SHADOW_REVIEW" for row in payload["agents"].values())),
        })
        mlflow.log_dict(payload, "evidence/council-agent-scores.json")
        return run.info.run_id


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Scikit-learn per-agent PAPER scoring. NO Council activation.")
    parser.add_argument("--journal", required=True, help="Actual append-only settled PAPER Council JSONL")
    parser.add_argument("--report", help="Optional research JSON path (never an active Council profile)")
    parser.add_argument("--mlflow-uri", help="Optional local MLflow tracking endpoint")
    args = parser.parse_args(argv)
    try:
        result = evaluate_paper_agents(args.journal)
        if args.mlflow_uri:
            result["mlflow_run_id"] = log_to_mlflow(result, uri=args.mlflow_uri)
        if args.report:
            _write_report(args.report, result)
        print(json.dumps({
            "status": result["status"],
            "source_sha256": result["source_sha256"],
            "unique_snapshots": result["unique_snapshots"],
            "agents": {k: {"status": v["status"], "candidate_weight": v["candidate_weight"]} for k, v in result["agents"].items()},
            "mlflow_run_id": result.get("mlflow_run_id"),
            "active_council_weights_changed": False,
            "live_trading_enabled": False,
        }, sort_keys=True))
        return 0
    except (ValueError, OSError, RuntimeError, ImportError) as exc:
        print(json.dumps({
            "status": "HOLD_BASELINE",
            "error": str(exc),
            "active_council_weights_changed": False,
            "live_trading_enabled": False,
        }), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
