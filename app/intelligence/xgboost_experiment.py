"""Offline, read-only evaluation of Council opinion reliability.

Never imported by the live/Paper decision path. Does not create execution intents,
change Council weights, or persist models.
"""

from __future__ import annotations

from collections import Counter
from math import isfinite
from typing import Any, Iterable

from app.intelligence.council_training import PaperTrainingExample, VALID_OUTCOMES


def prepare_snapshot_groups(
    examples: Iterable[PaperTrainingExample],
) -> list[list[tuple[dict[str, Any], int]]]:
    """Build chronological snapshot groups so a snapshot cannot cross the split."""
    groups: list[list[tuple[dict[str, Any], int]]] = []
    snapshots: set[str] = set()
    for example in examples:
        if not isinstance(example, PaperTrainingExample):
            raise ValueError("Expected settled PaperTrainingExample records")
        if example.execution_environment != "PAPER" or example.broker_execution_allowed:
            raise ValueError("Only non-broker PAPER outcomes are allowed")
        if example.snapshot_id in snapshots:
            raise ValueError(f"Duplicate snapshot_id: {example.snapshot_id}")
        snapshots.add(example.snapshot_id)
        if not example.opinions:
            raise ValueError(f"Council opinions missing for {example.snapshot_id}")

        seen_agents: set[str] = set()
        rows: list[tuple[dict[str, Any], int]] = []
        for opinion in example.opinions:
            if not isinstance(opinion, dict):
                raise ValueError("Council opinion must be an object")
            agent = str(opinion.get("agent", "")).strip()
            decision = str(opinion.get("decision", "")).upper()
            if not agent or agent in seen_agents:
                raise ValueError("Agent names must be present and unique per snapshot")
            seen_agents.add(agent)
            if decision not in VALID_OUTCOMES:
                raise ValueError("Unsupported Council opinion decision")
            if opinion.get("snapshot_id", example.snapshot_id) != example.snapshot_id:
                raise ValueError("Council opinion snapshot_id mismatch")
            try:
                confidence = float(opinion.get("confidence"))
            except (TypeError, ValueError) as exc:
                raise ValueError("Missing or invalid confidence") from exc
            if not isfinite(confidence) or not 0.0 <= confidence <= 1.0:
                raise ValueError("Confidence must be finite and between 0 and 1")
            rows.append(
                (
                    {"agent": agent, "decision": decision, "confidence": confidence},
                    int(decision == example.realized_direction),
                )
            )
        groups.append(rows)
    return groups


def evaluate_paper_examples(
    examples: Iterable[PaperTrainingExample],
    *,
    minimum_train_snapshots: int = 20,
    minimum_test_snapshots: int = 10,
    test_fraction: float = 0.2,
) -> dict[str, Any]:
    """Assess held-out opinion correctness, not trade returns or future certainty.

    Caller supplies examples in journal append order (oldest first). The final
    snapshot block is never involved in fitting preprocessing or the model.
    """
    if minimum_train_snapshots < 2 or minimum_test_snapshots < 2:
        raise ValueError("Minimum train/test snapshot counts must be at least 2")
    if not 0.0 < test_fraction < 1.0:
        raise ValueError("test_fraction must be between 0 and 1")
    groups = prepare_snapshot_groups(examples)
    holdout = max(minimum_test_snapshots, int(len(groups) * test_fraction))
    if len(groups) - holdout < minimum_train_snapshots:
        raise ValueError("Insufficient distinct settled PAPER snapshots for evaluation")

    train_rows = [row for group in groups[:-holdout] for row in group]
    test_rows = [row for group in groups[-holdout:] for row in group]
    train_labels = [label for _, label in train_rows]
    test_labels = [label for _, label in test_rows]
    if len(set(train_labels)) != 2 or len(set(test_labels)) != 2:
        raise ValueError("Both time partitions need correct and incorrect outcomes")

    try:
        import numpy as np
        from sklearn.feature_extraction import DictVectorizer
        from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
        from xgboost import XGBClassifier
    except ImportError as exc:
        raise RuntimeError("Install optional packages with requirements-ml.txt") from exc

    vectorizer = DictVectorizer(sparse=True)
    x_train = vectorizer.fit_transform([features for features, _ in train_rows])
    x_test = vectorizer.transform([features for features, _ in test_rows])
    classifier = XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        max_depth=2,
        learning_rate=0.05,
        n_estimators=80,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        reg_lambda=5.0,
        random_state=42,
        n_jobs=1,
    )
    classifier.fit(x_train, np.asarray(train_labels))
    probabilities = classifier.predict_proba(x_test)[:, 1]
    base_probability = float(sum(train_labels) / len(train_labels))
    baseline = np.full(len(test_labels), base_probability)

    model_brier = float(brier_score_loss(test_labels, probabilities))
    base_brier = float(brier_score_loss(test_labels, baseline))
    model_loss = float(log_loss(test_labels, probabilities, labels=[0, 1]))
    base_loss = float(log_loss(test_labels, baseline, labels=[0, 1]))

    def round_metric(value: float) -> float:
        return round(value, 6)

    return {
        "status": "EVALUATION_COMPLETE",
        "approval": "RESEARCH_ONLY",
        "training_environment": "PAPER",
        "broker_execution_allowed": False,
        "council_weights_modified": False,
        "model_persisted": False,
        "split": "chronological_by_snapshot_in_journal_order",
        "train_snapshots": len(groups) - holdout,
        "test_snapshots": holdout,
        "train_opinions": len(train_rows),
        "test_opinions": len(test_rows),
        "train_correctness_rate": round_metric(base_probability),
        "test_correctness_rate": round_metric(sum(test_labels) / len(test_labels)),
        "test_agents": dict(sorted(Counter(row[0]["agent"] for row in test_rows).items())),
        "metrics": {
            "xgboost_brier": round_metric(model_brier),
            "baseline_brier": round_metric(base_brier),
            "xgboost_log_loss": round_metric(model_loss),
            "baseline_log_loss": round_metric(base_loss),
            "xgboost_roc_auc": round_metric(float(roc_auc_score(test_labels, probabilities))),
        },
        "quality_gate": (
            "OBSERVATIONAL_IMPROVEMENT"
            if model_brier < base_brier and model_loss < base_loss
            else "NO_OBSERVED_IMPROVEMENT"
        ),
        "note": "Retrospective opinion correctness only; no verified profit or trading authorization.",
    }
