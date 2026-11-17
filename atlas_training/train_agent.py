"""ATLAS periodic agent training (upgraded with stability, calibration, and baseline gates).

Example:
  python atlas_training/train_agent_fixed.py --agent trend --csv data/XAUUSD_M15.csv

Requires a running MLflow server with model registry support.
Never submits orders, writes to the paper ledger, or changes live trading execution.
Enforces ATLAS Promotion Thresholds:
  - Baseline OOS floor (MIN_BASELINE_OOS = 0.525, i.e., >= 5% relative lift over 0.50 random baseline)
  - Minimum improvement over existing champion (MIN_IMPROVEMENT = 0.005)
  - Minimum OOS/Train stability ratio (MIN_STABILITY = 0.80)
  - Maximum calibration error (MAX_CALIBRATION_ERROR = 0.10)
"""
import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import TimeSeriesSplit

MIN_IMPROVEMENT = 0.005
MIN_BASELINE_OOS = 0.525
MIN_STABILITY = 0.80
MAX_CALIBRATION_ERROR = 0.10
REQUIRED = ("time", "open", "high", "low", "close")


def calibration_error(probabilities, labels, bins=10):
    """Weighted confidence-bin ECE; opposite bin errors cannot cancel."""
    probs = np.asarray(probabilities, dtype=float)
    labels = np.asarray(labels)
    if probs.shape != labels.shape or not len(probs) or not np.isfinite(probs).all():
        raise ValueError("Invalid calibration inputs")
    if ((probs < 0) | (probs > 1)).any():
        raise ValueError("Probabilities must be between 0 and 1")
    confidence = np.maximum(probs, 1 - probs)
    correct = ((probs >= .5).astype(int) == labels)
    bucket = np.minimum((confidence * bins).astype(int), bins - 1)
    return float(sum(np.mean(bucket == b) * abs(confidence[bucket == b].mean() - correct[bucket == b].mean())
                     for b in range(bins) if (bucket == b).any()))


def write_council_report(path, *, agent, metrics, eligible, reasons, run_id, version):
    """Publish review evidence atomically; never modifies Council weights."""
    payload = {
        "schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
        "agent": agent, "status": "SHADOW_REVIEW" if eligible else "REJECTED",
        "reviewers": ["STC-04", "STC-09"], "training_environment": "OFFLINE_RESEARCH",
        "broker_execution_allowed": False, "council_weight_activation": False,
        "illustrative_model": True, "run_id": run_id, "model_version": str(version),
        "metrics": metrics, "gate_reasons": reasons,
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=target.parent, prefix=".training-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, allow_nan=False, indent=2)
            handle.write("\n")
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return payload


def load_prices(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    missing = set(REQUIRED) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    df = df.loc[:, REQUIRED].copy()
    df["time"] = pd.to_datetime(df["time"], errors="raise", utc=True)
    for col in REQUIRED[1:]:
        df[col] = pd.to_numeric(df[col], errors="raise")
    if df.isna().any().any():
        raise ValueError("CSV contains null values")
    if df["time"].duplicated().any():
        raise ValueError("Duplicate timestamps")
    if not np.isfinite(df[list(REQUIRED[1:])].to_numpy()).all():
        raise ValueError("Prices must be finite")
    if (df[list(REQUIRED[1:])] <= 0).any().any():
        raise ValueError("Prices must be strictly positive")
    if ((df["high"] < df[["open", "close", "low"]].max(axis=1)) |
            (df["low"] > df[["open", "close", "high"]].min(axis=1))).any():
        raise ValueError("OHLC consistency check failed")
    df = df.sort_values("time").reset_index(drop=True)
    return df


def make_features(df: pd.DataFrame):
    """ILLUSTRATIVE: replace with real agent-specific features and target."""
    r = df["close"].pct_change()
    X = pd.DataFrame({f"ret_{k}": r.shift(k) for k in range(1, 9)})
    # Undefined next-bar return must not silently turn into class 0.
    future_return = r.shift(-1)
    y = (future_return > 0).astype("int64")
    valid = X.notna().all(axis=1) & future_return.notna()
    return X.loc[valid].reset_index(drop=True), y.loc[valid].reset_index(drop=True)


def make_model():
    """ILLUSTRATIVE: replace with real agent-specific model."""
    return GradientBoostingClassifier(random_state=7)


def walk_forward_metrics(X, y, folds=5):
    """Compute expanding-window OOS score, Train score, Stability (OOS/Train), and Calibration Error."""
    if folds < 2 or len(X) < max(100, (folds + 1) * 15):
        raise ValueError("Insufficient observations for meaningful walk-forward testing")
    if y.nunique() < 2:
        raise ValueError("Only one target class available")
    oos_scores = []
    train_scores = []
    cal_errors = []
    baseline_scores = []
    # gap=1 keeps the training labels from referring to an evaluation bar.
    for tr, te in TimeSeriesSplit(n_splits=folds, gap=1).split(X):
        if y.iloc[tr].nunique() < 2:
            raise ValueError("Training fold has only one target class")
        model = make_model().fit(X.iloc[tr], y.iloc[tr])
        tr_preds = model.predict(X.iloc[tr])
        te_preds = model.predict(X.iloc[te])
        tr_acc = float((tr_preds == y.iloc[tr].to_numpy()).mean())
        te_acc = float((te_preds == y.iloc[te].to_numpy()).mean())
        train_scores.append(tr_acc)
        oos_scores.append(te_acc)
        majority = int(y.iloc[tr].mode().iloc[0])
        baseline_scores.append(float((y.iloc[te] == majority).mean()))
        if hasattr(model, "predict_proba"):
            probs = model.predict_proba(X.iloc[te])[:, 1]
            cal_errors.append(calibration_error(probs, y.iloc[te].to_numpy()))
        else:
            raise ValueError("Model must provide probabilities for calibration review")
    oos_mean = float(np.mean(oos_scores))
    oos_std = float(np.std(oos_scores))
    train_mean = float(np.mean(train_scores))
    stability = float(oos_mean / train_mean) if train_mean > 0 else 0.0
    cal_error = float(np.mean(cal_errors))
    return {
        "oos_mean": oos_mean,
        "oos_std": oos_std,
        "oos_scores": oos_scores,
        "train_mean": train_mean,
        "stability": stability,
        "calibration_error": cal_error,
        "baseline_oos": float(np.mean(baseline_scores)),
    }


def walk_forward_score(X, y, folds=5):
    """Backward-compatible wrapper returning (mean, std, scores)."""
    m = walk_forward_metrics(X, y, folds=folds)
    return m["oos_mean"], m["oos_std"], m["oos_scores"]


def evaluate_promotion_gate(
    metrics: dict,
    previous_champion_score: float | None,
    min_improvement: float = MIN_IMPROVEMENT,
    min_baseline_oos: float = MIN_BASELINE_OOS,
    min_stability: float = MIN_STABILITY,
    max_calibration_error: float = MAX_CALIBRATION_ERROR,
) -> tuple[bool, list[str]]:
    """Verify candidate metrics against ATLAS Promotion Gates and Demotion Rules."""
    reasons = []
    for key in ("oos_mean", "stability", "calibration_error"):
        value = metrics.get(key)
        if value is None or not np.isfinite(value) or value < 0:
            return False, [f"Invalid metric: {key}"]
    if metrics["oos_mean"] > 1 or metrics["calibration_error"] > 1:
        return False, ["Accuracy and calibration metrics must be between 0 and 1"]
    if previous_champion_score is not None and (
        not np.isfinite(previous_champion_score) or not 0 <= previous_champion_score <= 1
    ):
        return False, ["Invalid champion score"]
    if "baseline_oos" in metrics:
        baseline = metrics["baseline_oos"]
        if not np.isfinite(baseline) or not 0 <= baseline <= 1:
            return False, ["Invalid baseline score"]
        min_baseline_oos = max(min_baseline_oos, baseline + min_improvement)
    oos = metrics["oos_mean"]
    stability = metrics["stability"]
    cal_err = metrics["calibration_error"]

    if oos < min_baseline_oos:
        reasons.append(f"OOS={oos:.4f} below baseline floor {min_baseline_oos:.4f}")
    if previous_champion_score is not None and oos < previous_champion_score + min_improvement:
        reasons.append(
            f"OOS={oos:.4f} below champion+margin ({previous_champion_score + min_improvement:.4f})"
        )
    if stability < min_stability:
        reasons.append(f"Stability={stability:.4f} below minimum {min_stability:.2f} (overfit risk)")
    if cal_err > max_calibration_error:
        reasons.append(
            f"Calibration error={cal_err:.4f} exceeds max {max_calibration_error:.2f}"
        )
    return len(reasons) == 0, reasons


def champion_score(client, name):
    """None means no champion alias; malformed champion metrics fail closed."""
    from mlflow.exceptions import MlflowException
    try:
        registered = client.get_registered_model(name)
    except MlflowException as exc:
        if getattr(exc, "error_code", None) in ("RESOURCE_DOES_NOT_EXIST",):
            return None
        raise
    # Existing models without an alias can use INVALID_PARAMETER_VALUE in MLflow.
    # Inspect explicit metadata rather than suppressing that broad error code.
    if "champion" not in registered.aliases:
        return None
    version = client.get_model_version_by_alias(name, "champion")
    score = client.get_run(version.run_id).data.metrics.get("oos_score")
    if score is None or not np.isfinite(score):
        raise ValueError("Champion OOS metric missing or invalid; manual review required")
    return float(score)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", required=True)
    parser.add_argument("--csv", required=True)
    parser.add_argument("--mlflow-uri", default="http://127.0.0.1:5000")
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--council-report", help="Write STC-04/STC-09 shadow review evidence JSON")
    parser.add_argument(
        "--promote",
        action="store_true",
        help="Allow champion promotion when all validation gates pass",
    )
    parser.add_argument(
        "--no-auto-promote",
        action="store_true",
        help="Force shadow review even if --promote is set",
    )
    args = parser.parse_args()

    import mlflow
    import mlflow.sklearn
    from mlflow import MlflowClient

    df = load_prices(args.csv)
    X, y = make_features(df)
    metrics = walk_forward_metrics(X, y, folds=args.folds)
    mean = metrics["oos_mean"]
    std = metrics["oos_std"]
    scores = metrics["oos_scores"]

    mlflow.set_tracking_uri(args.mlflow_uri)
    mlflow.set_experiment(f"atlas-agent-{args.agent}")
    name = f"atlas-{args.agent}"
    client = MlflowClient()
    previous = champion_score(client, name)
    eligible, gate_reasons = evaluate_promotion_gate(metrics, previous)

    with mlflow.start_run(run_name="periodic-retrain") as run:
        mlflow.log_params({
            "agent": args.agent,
            "rows": len(X),
            "csv": str(Path(args.csv)),
            "folds": args.folds,
            "purpose": "offline-research",
        })
        mlflow.log_metrics({
            "oos_score": mean,
            "oos_std": std,
            "train_score": metrics["train_mean"],
            "stability": metrics["stability"],
            "calibration_error": metrics["calibration_error"],
            "gate_eligible": 1.0 if eligible else 0.0,
        })
        for idx, score in enumerate(scores):
            mlflow.log_metric("fold_accuracy", score, step=idx)
        model = make_model().fit(X, y)
        # This model is fitted above in this process; trust only its reviewed tree storage type.
        mlflow.sklearn.log_model(
            model, name="model", input_example=X.head(3),
            serialization_format="skops", skops_trusted_types=["sklearn.tree._tree.Tree"],
        )
        run_id = run.info.run_id

    version = mlflow.register_model(f"runs:/{run_id}/model", name)
    client.set_registered_model_alias(name, "challenger", version.version)
    if args.council_report:
        write_council_report(args.council_report, agent=args.agent, metrics=metrics,
                             eligible=eligible, reasons=gate_reasons, run_id=run_id,
                             version=version.version)
    print(
        f"[REGISTERED CHALLENGER] {name} v{version.version} "
        f"OOS={mean:.4f} +/- {std:.4f} | Train={metrics['train_mean']:.4f} | "
        f"Stability={metrics['stability']:.4f} | CalErr={metrics['calibration_error']:.4f} | "
        f"champion={previous}"
    )
    if not eligible:
        print(f"[KEPT CHAMPION] Gate failed: {'; '.join(gate_reasons)}")
    elif args.no_auto_promote or not args.promote:
        print("[SHADOW REVIEW REQUIRED] Candidate passed validation gates; awaiting explicit promotion")
    else:
        client.set_registered_model_alias(name, "champion", version.version)
        print(f"[PROMOTED] {name} v{version.version}; registry alias updated (offline evaluation)")


if __name__ == "__main__":
    main()
