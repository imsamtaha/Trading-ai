"""Optional scikit-learn OFFLINE/SHADOW evaluation for ATLAS.

Reuses the repository's reviewed, illustrative OHLC feature builder and
walk-forward evaluation. Never imports MLflow, an MT5 adapter, or a broker.
Never installs Council weights, publishes a model, or places an order.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import sklearn
from sklearn.ensemble import GradientBoostingClassifier

from atlas_training.train_agent import (
    evaluate_promotion_gate,
    load_prices,
    make_features,
    walk_forward_metrics,
)


def backend_check() -> dict:
    """Fit a tiny in-memory classifier to verify the native Android/Windows stack."""
    x = np.arange(24, dtype=float).reshape(-1, 1)
    features = np.hstack((x, np.sin(x)))
    labels = (np.arange(24) % 2).astype(int)
    probabilities = GradientBoostingClassifier(
        random_state=7, n_estimators=8
    ).fit(features, labels).predict_proba(features)
    if probabilities.shape != (24, 2) or not np.isfinite(probabilities).all():
        raise RuntimeError("scikit-learn native fit/predict failed")
    return {
        "status": "READY_FOR_OFFLINE_RESEARCH",
        "backend": "scikit-learn",
        "sklearn_version": sklearn.__version__,
        "training_environment": "OFFLINE_RESEARCH",
        "broker_execution_allowed": False,
        "council_weight_activation": False,
        "model_registered": False,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def evaluate_csv(path: str | Path, *, agent: str, folds: int = 5) -> dict:
    """Read only an OHLC CSV, fit ephemeral models, and return review evidence."""
    if not agent.strip():
        raise ValueError("agent must not be empty")
    source = Path(path)
    fingerprint = _sha256(source)
    df = load_prices(str(source))
    x, y = make_features(df)
    metrics = walk_forward_metrics(x, y, folds=folds)
    thresholds_passed, reasons = evaluate_promotion_gate(
        metrics, previous_champion_score=None
    )
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "SHADOW_REVIEW" if thresholds_passed else "REJECTED",
        "backend": "scikit-learn",
        "sklearn_version": sklearn.__version__,
        "agent": agent,
        "training_environment": "OFFLINE_RESEARCH",
        "source_kind": "OHLC_CSV",
        "source_sha256": fingerprint,
        "source_rows": len(df),
        "evaluation_rows": len(x),
        "feature_scope": "ILLUSTRATIVE_NOT_LIVE_SIGNALS",
        "reviewers": ["STC-04", "STC-09"],
        "metrics": metrics,
        "thresholds_passed": thresholds_passed,
        "gate_reasons": reasons,
        "broker_execution_allowed": False,
        "council_weight_activation": False,
        "model_registered": False,
        "champion_promoted": False,
    }


def write_shadow_report(path: str | Path, result: dict) -> Path:
    """Atomically replace an *explicit* research report; never touch Paper ledgers."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        dir=target.parent, prefix=".sklearn-shadow-", suffix=".json"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ATLAS scikit-learn offline shadow evaluation (no broker/MLflow)."
    )
    parser.add_argument("--check", action="store_true", help="In-memory native backend smoke check")
    parser.add_argument("--csv", help="Existing chronological OHLC CSV; never generated here")
    parser.add_argument("--agent", default="research", help="Review label only, not a Council install")
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--report", help="Optional standalone research JSON output path")
    args = parser.parse_args(argv)

    if args.check and (args.csv or args.report):
        parser.error("--check cannot be combined with --csv or --report")
    if not args.check and not args.csv:
        parser.error("--csv is required unless --check is specified")

    try:
        result = backend_check() if args.check else evaluate_csv(
            args.csv, agent=args.agent, folds=args.folds
        )
        if args.report:
            write_shadow_report(args.report, result)
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({
            "status": "ERROR", "reason": str(exc),
            "broker_execution_allowed": False,
            "council_weight_activation": False,
        }), file=sys.stderr)
        return 2
    print(json.dumps(result, allow_nan=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
