"""Independent offline regime/alpha models. Risk policy has no learned override."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import uuid
import zipfile

from app.intelligence.specialists import specialist_contracts


class SpecialistModel:
    def __init__(self, role):
        if role not in {"macro_analyst", "quantitative_strategist"}:
            raise ValueError("Only Macro/Quant are trainable; Risk Executive is deterministic")
        self.role = role
        self.contract = specialist_contracts()[role]
        self.model = None
        self.metadata = None

    def _features(self, frame):
        import numpy as np
        if set(frame.columns) != set(self.contract['features']) or not frame.columns.is_unique:
            raise ValueError("Wrong specialist feature schema")
        values = frame[self.contract['features']].astype(float)
        if not np.isfinite(values.to_numpy()).all() or (np.abs(values.to_numpy()) > 1e12).any():
            raise ValueError("Finite specialist features are required")
        if self.role == 'macro_analyst' and not values.order_flow_imbalance.between(-1, 1).all():
            raise ValueError("Order-flow imbalance must be -1..1")
        if self.role == 'quantitative_strategist' and (values.transaction_cost_bps < 0).any():
            raise ValueError("Transaction costs cannot be negative")
        return values

    def fit(self, frame, *, confirmed_observed=False):
        import numpy as np
        import pandas as pd
        import xgboost as xgb
        from sklearn.metrics import accuracy_score, log_loss, mean_absolute_error
        if confirmed_observed is not True:
            raise ValueError("Explicit observed-data confirmation required")
        target = self.contract['training_target']
        required = set(self.contract['features']) | {target, 'snapshot_at', 'available_at', 'label_available_at', 'source'}
        if not required.issubset(frame.columns) or not 50 <= len(frame) <= 10000:
            raise ValueError("Need 50..10000 complete specialist records")
        data = frame.copy()
        allowed_sources = {'observed'} if self.role == 'macro_analyst' else {'observed', 'paper'}
        if not set(data.source).issubset(allowed_sources):
            raise ValueError("Unsupported source for this specialist target")
        for key in ['snapshot_at', 'available_at', 'label_available_at']:
            # Require explicit timezone; never silently reinterpret local dates.
            from app.intelligence.specialists import timestamp
            data[key] = pd.to_datetime([timestamp(value) for value in data[key]], utc=True)
        now = datetime.now(timezone.utc)
        if (data.available_at > data.snapshot_at).any() or (data.label_available_at <= data.snapshot_at).any() or (data.label_available_at > now).any():
            raise ValueError("Features must be known at prediction time and targets must be settled")
        data = data.sort_values('snapshot_at', kind='stable').reset_index(drop=True)
        X = self._features(data[self.contract['features']])
        bounds = np.flatnonzero(data.snapshot_at.to_numpy()[1:] != data.snapshot_at.to_numpy()[:-1]) + 1
        if len(bounds) < 2:
            raise ValueError("Need at least three distinct snapshot groups")
        # Whole-group chronological boundaries. Ratios are nominal, not a reason
        # to divide simultaneous records across training and evaluation.
        a = int(min(bounds[:-1], key=lambda cut: (abs(cut - len(data) * .6), cut)))
        b = int(min(bounds[bounds > a], key=lambda cut: (abs(cut - len(data) * .8), cut)))
        training = np.flatnonzero((data.index < a) & (data.label_available_at < data.snapshot_at.iloc[a]))
        validation = np.flatnonzero((data.index >= a) & (data.index < b) & (data.label_available_at < data.snapshot_at.iloc[b]))
        test = np.arange(b, len(data))
        if min(len(training), len(validation), len(test)) < 5:
            raise ValueError("Insufficient settled rows after chronological label purging")
        params = dict(max_depth=3, learning_rate=.05, n_estimators=150, subsample=.8,
                      colsample_bytree=.8, random_state=42, n_jobs=1, tree_method='hist', early_stopping_rounds=15)
        classes = None
        if self.role == 'macro_analyst':
            labels = data[target]
            if not labels.map(lambda x: isinstance(x, str) and 0 < len(x.strip()) <= 50).all():
                raise ValueError("Structural regime labels are required")
            classes = sorted(labels.unique())
            if len(classes) < 2 or len(classes) > 20 or set(labels.iloc[training]) != set(classes):
                raise ValueError("Training history must represent all structural regimes")
            y = np.array([classes.index(value) for value in labels])
            model = xgb.XGBClassifier(objective='multi:softprob', num_class=len(classes), eval_metric='mlogloss', **params)
        else:
            y = data[target].to_numpy(dtype=float)
            if not np.isfinite(y).all() or (np.abs(y) > 1e6).any():
                raise ValueError("Finite net returns are required")
            model = xgb.XGBRegressor(objective='reg:squarederror', eval_metric='rmse', **params)
        model.fit(X.iloc[training], y[training], eval_set=[(X.iloc[validation], y[validation])], verbose=False)
        if classes:
            probabilities = model.predict_proba(X.iloc[test])
            metrics = {'logloss': float(log_loss(y[test], probabilities, labels=np.arange(len(classes)))),
                       'accuracy': float(accuracy_score(y[test], probabilities.argmax(axis=1)))}
            majority = int(np.bincount(y[training]).argmax())
            baseline = {'accuracy': float(np.mean(y[test] == majority))}
        else:
            predictions = model.predict(X.iloc[test])
            metrics = {'mae': float(mean_absolute_error(y[test], predictions))}
            baseline = {'mae': float(mean_absolute_error(y[test], np.full(len(test), np.median(y[training]))))}
        metadata = dict(schema_version=1, role=self.role, target=target, features=self.contract['features'],
            purpose=self.role+'_advisory', production_ready=False, broker_execution_allowed=False,
            session_id=uuid.uuid4().hex, trained_at_utc=now.isoformat(), sources=sorted(set(data.source)),
            dataset_sha256=hashlib.sha256(data[sorted(required)].to_csv(index=False).encode()).hexdigest(),
            rows_train=len(training), rows_validation=len(validation), rows_test=len(test),
            rows_purged=len(data)-len(training)-len(validation)-len(test), metrics=metrics, baselines=baseline,
            classes=classes, best_iteration=int(model.best_iteration), xgboost_version=xgb.__version__,
            time_ranges={name: {'start': data.snapshot_at.iloc[part[0]].isoformat(),
                                'end': data.snapshot_at.iloc[part[-1]].isoformat()}
                         for name, part in [('train',training),('validation',validation),('test',test)]})
        self.model, self.metadata = model, metadata
        return metadata

    def predict(self, features):
        if self.model is None:
            raise RuntimeError("Specialist model is not trained")
        X = self._features(features)
        return self.model.predict_proba(X) if self.role == 'macro_analyst' else self.model.predict(X)

    def save(self, directory):
        if self.model is None:
            raise RuntimeError("Specialist model is not trained")
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / self.contract['model_file']
        with tempfile.TemporaryDirectory(dir=directory) as temp:
            model_path = Path(temp)/'model.json'
            self.model.save_model(model_path)
            payload = model_path.read_bytes()
        metadata = dict(self.metadata, model_sha256=hashlib.sha256(payload).hexdigest())
        fd, name = tempfile.mkstemp(dir=directory, suffix='.tmp', prefix=self.role+'.')
        try:
            with os.fdopen(fd, 'w+b') as handle:
                with zipfile.ZipFile(handle, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
                    bundle.writestr('model.json', payload)
                    bundle.writestr('metadata.json', json.dumps(metadata, allow_nan=False))
                handle.flush();os.fsync(handle.fileno())
            os.replace(name, destination)
        finally:
            Path(name).unlink(missing_ok=True)
        return destination

    @classmethod
    def load(cls, directory, role):
        import xgboost as xgb
        result = cls(role)
        path = Path(directory)/result.contract['model_file']
        if path.stat().st_size > 32*1024*1024:
            raise ValueError("Specialist bundle too large")
        with zipfile.ZipFile(path) as bundle:
            if set(bundle.namelist()) != {'model.json','metadata.json'} or len(bundle.namelist()) != 2 or any(item.file_size > 32*1024*1024 for item in bundle.infolist()):
                raise ValueError("Invalid specialist bundle")
            def reject(value): raise ValueError('Nonfinite metadata')
            metadata = json.loads(bundle.read('metadata.json'), parse_constant=reject)
            payload = bundle.read('model.json')
        if (not isinstance(metadata, dict) or metadata.get('schema_version') != 1 or metadata.get('role') != role
                or metadata.get('features') != result.contract['features'] or metadata.get('target') != result.contract['training_target']
                or metadata.get('purpose') != role+'_advisory' or metadata.get('production_ready') is not False
                or metadata.get('broker_execution_allowed') is not False
                or hashlib.sha256(payload).hexdigest() != metadata.get('model_sha256')):
            raise ValueError("Specialist schema/provenance/checksum mismatch")
        from math import isfinite
        sources = metadata.get('sources')
        allowed = {'observed'} if role == 'macro_analyst' else {'observed','paper'}
        if not isinstance(sources, list) or not sources or not set(sources).issubset(allowed):
            raise ValueError('Invalid specialist training sources')
        for key in ['metrics','baselines']:
            values = metadata.get(key)
            if not isinstance(values, dict) or not values or any(type(v) not in (int,float) or not isfinite(v) or v < 0 for v in values.values()):
                raise ValueError('Invalid specialist evaluation')
        if any(type(metadata.get(key)) is not int or not 5 <= metadata[key] <= 10000 for key in ['rows_train','rows_validation','rows_test']):
            raise ValueError('Invalid specialist training counts')
        from app.intelligence.specialists import timestamp
        timestamp(metadata.get('trained_at_utc'))
        classes = metadata.get('classes')
        if role == 'macro_analyst' and (not isinstance(classes, list) or not 2 <= len(classes) <= 20
                or not all(isinstance(x,str) and 0 < len(x.strip()) <= 50 for x in classes) or len(set(classes)) != len(classes)):
            raise ValueError('Invalid regime labels')
        if role == 'quantitative_strategist' and classes is not None:
            raise ValueError('Wrong target type')
        model = xgb.XGBClassifier(n_jobs=1) if role == 'macro_analyst' else xgb.XGBRegressor(n_jobs=1)
        model.load_model(bytearray(payload))
        if model.get_booster().feature_names != result.contract['features'] or (role == 'macro_analyst' and model.n_classes_ != len(classes)):
            raise ValueError('Native specialist schema mismatch')
        result.model, result.metadata = model, metadata
        return result
