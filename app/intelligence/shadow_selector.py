"""Paper-only entry/abstention research; never changes execution decisions."""
from __future__ import annotations
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from app.strategy.universe import classify_symbol, normalize_symbol

CLASSES = ("FOREX", "METALS", "ENERGY", "INDICES", "CRYPTO", "STOCKS", "COMMODITIES")

def stamp(value):
    result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timezone required")
    return result.astimezone(timezone.utc)

def sigmoid(value):
    return 1 / (1 + math.exp(-max(-40, min(40, value))))

def train(xs, ys, epochs=400, regularization=.05):
    weights = [0.] * len(xs[0])
    for _ in range(epochs):
        gradients = [0.] * len(weights)
        for x, y in zip(xs, ys):
            error = sigmoid(sum(w*v for w,v in zip(weights,x))) - y
            for j,v in enumerate(x):
                gradients[j] += error*v
        weights = [w-.2*(g/len(xs)+(regularization*w if j else 0))
                   for j,(w,g) in enumerate(zip(weights,gradients))]
    return weights

class ShadowSelector:
    """Deterministic L2 logistic model with chronological Platt calibration.

    Minimum counts are operational gates, not statistical proof of performance.
    All historical reports are exploratory; fresh predictions are separately logged.
    """
    def __init__(self, minimum_samples=100, minimum_days=3):
        self.minimum_samples = minimum_samples
        self.minimum_days = minimum_days
        self.weights = None
        self.calibrator = None
        self.support = set()
        self.report = {}

    @staticmethod
    def features(row):
        confidence = float(row.get("confidence", 0))
        if not math.isfinite(confidence) or not 0 <= confidence <= 100:
            raise ValueError("Invalid confidence")
        opened = stamp(row.get("opened_at") or row.get("timestamp"))
        asset = (classify_symbol(normalize_symbol(str(row.get("symbol", "")))) or ("UNKNOWN", 3))[0]
        strategy = str(row.get("strategy", ""))
        direction = str(row.get("direction", "")).upper()
        if direction not in {"LONG", "SHORT"}:
            raise ValueError("Invalid direction")
        hour = opened.hour + opened.minute / 60
        return [1., confidence/100, float(direction=="LONG"),
                math.sin(hour*math.pi/12), math.cos(hour*math.pi/12),
                float(strategy=="CONTINUATION_5M"), float(strategy=="LIQUIDITY_RECLAIM"),
                *[float(asset==category) for category in CLASSES]]

    @staticmethod
    def _support(row):
        return (normalize_symbol(str(row.get("symbol", ""))), str(row.get("strategy", "")))

    def _raw_score(self, row):
        return sum(w*v for w,v in zip(self.weights,self.features(row)))

    def predict(self, row):
        result = dict(mode="SHADOW", broker_execution_allowed=False,
                      changes_trade_decision=False, probability=None,
                      model_generated_at=self.report.get("generated_at"),
                      trained_through=self.report.get("trained_through"),
                      recommendation="ABSTAIN", status="INSUFFICIENT_DATA")
        if self.weights is None:
            return result
        if self._support(row) not in self.support:
            result["status"] = "UNSEEN_SYMBOL_OR_STRATEGY"
            return result
        score = self._raw_score(row)
        p = sigmoid(self.calibrator[0] + self.calibrator[1]*score)
        result.update(probability=round(p,6),
                      recommendation="ENTER" if p >= .8 else "ABSTAIN",
                      status="SHADOW_ONLY")
        return result

    def fit(self, rows):
        self.weights = self.calibrator = None
        self.support = set()
        valid, seen, invalid, duplicates = [], set(), 0, 0
        now = datetime.now(timezone.utc)
        for row in rows:
            try:
                if row.get("status") != "CLOSED" or row.get("broker_execution_allowed", False):
                    raise ValueError("Only settled paper outcomes")
                if str(row.get("execution_environment", "PAPER")).upper() != "PAPER":
                    raise ValueError("Only PAPER")
                opened, closed = stamp(row["opened_at"]), stamp(row["closed_at"])
                r = float(row["r_multiple"])
                if not math.isfinite(r) or not opened <= closed <= now:
                    raise ValueError("Invalid outcome or time")
                self.features(row)
                identity = str(row["id"])
                if not identity:
                    raise ValueError("ID required")
                if identity in seen:
                    duplicates += 1
                    continue
                seen.add(identity)
                valid.append(dict(row))
            except (ValueError, TypeError, KeyError, OverflowError):
                invalid += 1
        valid.sort(key=lambda row: (stamp(row["opened_at"]), str(row["id"])))
        days = len({stamp(row["opened_at"]).date() for row in valid})
        report = dict(version=1, generated_at=now.isoformat(), mode="SHADOW",
                      status="INSUFFICIENT_DATA", broker_execution_allowed=False,
                      changes_trade_decision=False, samples=len(valid), independent_days=days,
                      minimum_samples=self.minimum_samples, minimum_days=self.minimum_days,
                      invalid_records=invalid, duplicate_records=duplicates,
                      threshold=.8, daily_entry_ceiling=100,
                      outcome="positive risk-normalized paper R; spread included; fees excluded",
                      evaluation="exploratory chronological; not independent forward proof")
        self.report = report
        if len(valid) < self.minimum_samples or days < self.minimum_days:
            return report
        a,b = int(len(valid)*.6), int(len(valid)*.8)
        calibration, test = valid[a:b], valid[b:]
        train_rows = [r for r in valid[:a] if stamp(r["closed_at"]) < stamp(calibration[0]["opened_at"])]
        calibration_rows = [r for r in calibration if stamp(r["closed_at"]) < stamp(test[0]["opened_at"])]
        report.update(purged_train=a-len(train_rows), purged_calibration=len(calibration)-len(calibration_rows))
        if len(train_rows)<30 or len(calibration_rows)<10 or len(test)<10:
            report["status"] = "INSUFFICIENT_AFTER_PURGE"
            return report
        ys = [float(r["r_multiple"]>0) for r in train_rows]
        cys = [float(r["r_multiple"]>0) for r in calibration_rows]
        if len(set(ys))<2 or len(set(cys))<2:
            report["status"] = "INSUFFICIENT_LABEL_VARIATION"
            return report
        self.weights = train([self.features(r) for r in train_rows],ys)
        self.calibrator = train([[1.,self._raw_score(r)] for r in calibration_rows],cys)
        self.support = {self._support(r) for r in train_rows}
        scored = [(r,self.predict(r)) for r in test]
        covered = [(r,p) for r,p in scored if p["probability"] is not None]
        selected = [r for r,p in covered if p["recommendation"]=="ENTER"]
        gains = sum(max(0,float(r["r_multiple"])) for r in selected)
        losses = -sum(min(0,float(r["r_multiple"])) for r in selected)
        cumulative, peak, drawdown = 0.,0.,0.
        for row in selected:
            cumulative += float(row["r_multiple"])
            peak = max(peak,cumulative)
            drawdown = max(drawdown,peak-cumulative)
        report.update(status="SHADOW_ONLY", train_samples=len(train_rows),
                      calibration_samples=len(calibration_rows),
                      trained_through=max(r["closed_at"] for r in calibration_rows),
                      weights=self.weights, calibrator=self.calibrator,
                      supported_pairs=sorted(self.support),
                      test=dict(samples=len(test), supported=len(covered), selected=len(selected),
                                coverage=len(selected)/len(test),
                                baseline_sum_r=sum(float(r["r_multiple"]) for r in test),
                                selected_sum_r=cumulative, max_drawdown_r=drawdown,
                                profit_factor_r=gains/losses if losses else None,
                                brier=(sum((p["probability"]-float(r["r_multiple"]>0))**2 for r,p in covered)/len(covered)) if covered else None))
        return report

    def save_report(self,path):
        target = Path(path)
        target.parent.mkdir(parents=True,exist_ok=True)
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.report,indent=2,allow_nan=False)+"\n",encoding="utf-8")
        os.replace(temporary,target)
