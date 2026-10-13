"""Bounded, advisory customer-routing scores; never a trading execution model."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import zipfile

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import log_loss, mean_absolute_error, mean_squared_error, roc_auc_score
from sklearn.model_selection import train_test_split

FEATURES = (
    "agent_experience_months", "avg_handle_time_mins", "historical_csat",
    "total_chats_handled", "current_workload",
)


class AgentPerformanceXGBoost:
    def __init__(self):
        self._lock = threading.RLock()
        self.sales_model, self.csat_model = self._new_models()
        self.metadata = None

    @staticmethod
    def _new_models():
        params = dict(max_depth=5, learning_rate=.05, n_estimators=150,
                      subsample=.8, colsample_bytree=.8, random_state=42,
                      n_jobs=1, tree_method="hist", early_stopping_rounds=15)
        return (xgb.XGBClassifier(objective="binary:logistic", eval_metric="logloss", **params),
                xgb.XGBRegressor(objective="reg:squarederror", eval_metric="rmse", **params))

    @staticmethod
    def _features(X):
        if not isinstance(X, pd.DataFrame) or not X.columns.is_unique:
            raise ValueError("Features must be a DataFrame with unique columns")
        if set(X.columns) != set(FEATURES):
            raise ValueError("Expected exactly these features: " + ", ".join(FEATURES))
        try:
            X = X.loc[:, list(FEATURES)].astype(float)
        except (TypeError, ValueError) as exc:
            raise ValueError("Features must be numeric") from exc
        if not np.isfinite(X.to_numpy()).all() or (X < 0).any().any():
            raise ValueError("Features must be finite and nonnegative")
        if (X.to_numpy() > np.finfo(np.float32).max).any():
            raise ValueError("Features exceed the model numeric range")
        if not X.historical_csat.between(1, 5).all() or (X.avg_handle_time_mins <= 0).any():
            raise ValueError("CSAT must be 1..5 and handle time positive")
        counts = X[["agent_experience_months", "total_chats_handled", "current_workload"]].to_numpy()
        if not np.equal(counts, np.floor(counts)).all():
            raise ValueError("Experience, chats and workload must be integer counts")
        return X

    @staticmethod
    def generate_synthetic_data(num_samples=1000):
        if not isinstance(num_samples, int) or num_samples < 1:
            raise ValueError("num_samples must be a positive integer")
        rng = np.random.default_rng(42)
        X = pd.DataFrame({
            "agent_experience_months": rng.integers(1, 48, num_samples),
            "avg_handle_time_mins": rng.uniform(3, 25, num_samples),
            "historical_csat": rng.uniform(1, 5, num_samples),
            "total_chats_handled": rng.integers(50, 2000, num_samples),
            "current_workload": rng.integers(0, 5, num_samples),
        })
        logits = X.agent_experience_months * .05 - X.avg_handle_time_mins * .1 + X.historical_csat * .4
        sales = rng.binomial(1, 1 / (1 + np.exp(-logits)))
        csat = np.clip(2 + X.agent_experience_months * .02 - X.current_workload * .3
                       + X.historical_csat * .4 + rng.normal(0, .2, num_samples), 1, 5)
        return X, sales, csat.to_numpy()

    def train(self, X, y_sales, y_csat, *, source="observed", split="chronological"):
        X = self._features(X)
        ys, yc = np.asarray(y_sales, dtype=float), np.asarray(y_csat, dtype=float)
        if len(X) < 50 or ys.shape != (len(X),) or yc.shape != (len(X),):
            raise ValueError("Need at least 50 aligned feature and target rows")
        if not np.isfinite(ys).all() or not np.isfinite(yc).all():
            raise ValueError("Targets must be finite")
        if set(np.unique(ys)) != {0, 1} or not ((yc >= 1) & (yc <= 5)).all():
            raise ValueError("Sales needs both binary classes; CSAT must be 1..5")
        if source not in {"observed", "synthetic"} or split not in {"chronological", "random"}:
            raise ValueError("Unsupported source or split")
        if source == "observed" and split != "chronological":
            raise ValueError("Observed data requires chronological validation")
        indices = np.arange(len(X))
        if split == "random":
            development, test = train_test_split(indices, test_size=.2, random_state=42, stratify=ys)
            training, validation = train_test_split(development, test_size=.25, random_state=42,
                                                    stratify=ys[development])
        else:
            training, validation, test = np.split(indices, [int(len(X) * .6), int(len(X) * .8)])
        if any(set(np.unique(ys[part])) != {0, 1} for part in (training, validation, test)):
            raise ValueError("Each split needs both sales classes")
        sales, csat = self._new_models()
        # Training happens separately from request-time inference. Publish only a complete pair.
        sales.fit(X.iloc[training], ys[training], eval_set=[(X.iloc[validation], ys[validation])], verbose=False)
        csat.fit(X.iloc[training], yc[training], eval_set=[(X.iloc[validation], yc[validation])], verbose=False)
        probabilities = sales.predict_proba(X.iloc[test])[:, 1]
        predictions = np.clip(csat.predict(X.iloc[test]), 1, 5)
        meta = dict(schema_version=1, source=source, split=split, production_ready=False,
                    purpose="customer_routing_advisory", features=list(FEATURES),
                    trained_at_utc=datetime.now(timezone.utc).isoformat(),
                    rows_train=len(training), rows_validation=len(validation), rows_test=len(test),
                    xgboost_version=xgb.__version__, metrics={
                        "sales_auc": float(roc_auc_score(ys[test], probabilities)),
                        "sales_logloss": float(log_loss(ys[test], probabilities)),
                        "csat_mae": float(mean_absolute_error(yc[test], predictions)),
                        "csat_rmse": float(np.sqrt(mean_squared_error(yc[test], predictions))),
                    })
        with self._lock:
            self.sales_model, self.csat_model, self.metadata = sales, csat, meta
        return meta

    def predict_composite_score(self, current_agents_features, w_sales=.6, w_csat=.4):
        weights = np.asarray([w_sales, w_csat], dtype=float)
        if not np.isfinite(weights).all() or (weights < 0).any() or not np.isclose(weights.sum(), 1):
            raise ValueError("Weights must be nonnegative, finite and sum to 1")
        w_sales, w_csat = weights / weights.sum()
        X = self._features(current_agents_features)
        with self._lock:
            if self.metadata is None:
                raise RuntimeError("Model is not trained")
            if X.empty:
                return np.array([]), np.array([]), np.array([])
            probabilities = self.sales_model.predict_proba(X)[:, 1]
            predictions = np.clip(self.csat_model.predict(X), 1, 5)
        # CSAT has a known domain. Training-sample min/max can send future scores outside [0,1].
        scores = np.clip(w_sales * probabilities + w_csat * ((predictions - 1) / 4), 0, 1)
        return scores, probabilities, predictions

    def save_models(self, path_prefix="agent_xgb"):
        destination = Path(str(path_prefix) + ".bundle.zip")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            if self.metadata is None:
                raise RuntimeError("Model is not trained")
            with tempfile.TemporaryDirectory(prefix="agent-model-", dir=destination.parent) as scratch:
                sales_path, csat_path = Path(scratch) / "sales.json", Path(scratch) / "csat.json"
                self.sales_model.save_model(sales_path)
                self.csat_model.save_model(csat_path)
                files = {"sales.json": sales_path.read_bytes(), "csat.json": csat_path.read_bytes()}
            meta = dict(self.metadata, sha256={name: hashlib.sha256(data).hexdigest() for name, data in files.items()})
        fd, name = tempfile.mkstemp(prefix=destination.name + ".", suffix=".tmp", dir=destination.parent)
        try:
            with os.fdopen(fd, "w+b") as handle:
                with zipfile.ZipFile(handle, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
                    for key, value in files.items():
                        bundle.writestr(key, value)
                    bundle.writestr("metadata.json", json.dumps(meta, allow_nan=False))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(name, destination)
        finally:
            Path(name).unlink(missing_ok=True)
        return destination

    @classmethod
    def load_models(cls, path_prefix="agent_xgb"):
        path = Path(str(path_prefix) + ".bundle.zip")
        if path.stat().st_size > 32 * 1024 * 1024:
            raise ValueError("Model bundle is too large")
        with zipfile.ZipFile(path) as bundle:
            if len(bundle.namelist()) != 3 or set(bundle.namelist()) != {"sales.json", "csat.json", "metadata.json"}:
                raise ValueError("Invalid model bundle")
            if any(item.file_size > 32 * 1024 * 1024 for item in bundle.infolist()):
                raise ValueError("Model payload is too large")
            meta = json.loads(bundle.read("metadata.json"), parse_constant=cls._reject_json_constant)
            if not isinstance(meta, dict):
                raise ValueError("Invalid model metadata")
            if meta.get("schema_version") != 1 or meta.get("features") != list(FEATURES):
                raise ValueError("Unsupported model schema")
            if meta.get("source") not in {"observed", "synthetic"} or meta.get("production_ready") is not False:
                raise ValueError("Invalid model provenance")
            if meta.get("purpose") != "customer_routing_advisory" or not isinstance(meta.get("sha256"), dict):
                raise ValueError("Invalid model purpose or checksums")
            if meta.get("split") not in {"chronological", "random"}:
                raise ValueError("Invalid validation split")
            if meta["source"] == "observed" and meta["split"] != "chronological":
                raise ValueError("Observed model requires chronological validation")
            metrics = meta.get("metrics", {})
            if not isinstance(metrics, dict):
                raise ValueError("Invalid model metrics")
            for key in ("sales_auc", "sales_logloss", "csat_mae", "csat_rmse"):
                value = metrics.get(key)
                if type(value) not in (int, float) or not np.isfinite(value) or value < 0:
                    raise ValueError("Invalid model metric: " + key)
            if metrics["sales_auc"] > 1:
                raise ValueError("Invalid model AUC")
            if any(type(meta.get(key)) is not int or meta[key] < 1
                   for key in ("rows_train", "rows_validation", "rows_test")):
                raise ValueError("Invalid training row counts")
            trained = datetime.fromisoformat(meta.get("trained_at_utc", ""))
            if trained.tzinfo is None or not isinstance(meta.get("xgboost_version"), str):
                raise ValueError("Invalid model training information")
            files = {key: bundle.read(key) for key in ("sales.json", "csat.json")}
        if any(hashlib.sha256(data).hexdigest() != meta.get("sha256", {}).get(key) for key, data in files.items()):
            raise ValueError("Model checksum mismatch")
        model = cls()
        model.sales_model.load_model(bytearray(files["sales.json"]))
        model.csat_model.load_model(bytearray(files["csat.json"]))
        model.sales_model.set_params(n_jobs=1)
        model.csat_model.set_params(n_jobs=1)
        model.metadata = meta
        return model

    @staticmethod
    def _reject_json_constant(value):
        raise ValueError("Nonfinite model metadata: " + value)
