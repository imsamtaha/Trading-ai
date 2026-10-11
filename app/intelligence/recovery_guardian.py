from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
from math import isfinite
import os
from pathlib import Path
import tempfile
import time


class RecoveryGuardian:
    """Veto-only Paper supervisor. Historical diagnostics are not a profit forecast."""

    NAME = "ATLAS Recovery Guardian"

    def __init__(self, *, minimum_samples=10, minimum_days=3, window=20, max_spread_fraction=0.25):
        if not 1 <= minimum_samples <= window or minimum_days < 1:
            raise ValueError("Invalid recovery evidence limits")
        if not isfinite(max_spread_fraction) or not 0 < max_spread_fraction <= 1:
            raise ValueError("Invalid recovery spread limit")
        self.minimum_samples = minimum_samples
        self.minimum_days = minimum_days
        self.window = window
        self.max_spread_fraction = max_spread_fraction
        self.closed_examples = self.invalid_outcomes = self.duplicates_ignored = self.excluded_future = 0
        self.pairs = {}

    @staticmethod
    def _stamp(value):
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("Recovery evidence needs an explicit timezone")
        return parsed.astimezone(timezone.utc)

    def fit(self, rows, *, as_of=None):
        cutoff = self._stamp(as_of or datetime.now(timezone.utc))
        self.closed_examples = self.invalid_outcomes = self.duplicates_ignored = self.excluded_future = 0
        self.pairs = {}
        grouped, seen = defaultdict(list), {}
        for row in rows:
            try:
                if not isinstance(row, dict) or row.get("status") != "CLOSED":
                    raise ValueError("Not a settled Paper outcome")
                intent = row.get("training_context", {}).get("trade_intent", {})
                if intent.get("execution_environment") != "PAPER" or intent.get("broker_execution_allowed") is not False:
                    raise ValueError("Invalid Paper provenance")
                identifier, symbol, strategy = (row.get(k) for k in ("id", "symbol", "strategy"))
                if not all(isinstance(v, str) and 0 < len(v) <= 160 for v in (identifier, symbol, strategy)):
                    raise ValueError("Invalid Paper identifier")
                result = row.get("r_multiple")
                if type(result) not in (int, float) or not isfinite(result):
                    raise ValueError("Nonfinite outcome")
                stamp = self._stamp(row.get("closed_at"))
                if stamp > cutoff:
                    self.excluded_future += 1
                    continue
                if identifier in seen:
                    if seen[identifier] != row:
                        raise ValueError("Conflicting duplicate outcome")
                    self.duplicates_ignored += 1
                    continue
                seen[identifier] = row
                grouped[(symbol.upper(), strategy.upper())].append((stamp, result))
                self.closed_examples += 1
            except (ValueError, TypeError, AttributeError):
                self.invalid_outcomes += 1
        for (symbol, strategy), outcomes in sorted(grouped.items()):
            recent = sorted(outcomes, key=lambda item: item[0], reverse=True)[:self.window]
            days = len({stamp.date() for stamp, _ in recent})
            mean = sum(result for _, result in recent) / len(recent)
            supported = len(recent) >= self.minimum_samples and days >= self.minimum_days
            self.pairs[(symbol, strategy)] = {
                "symbol": symbol, "strategy": strategy, "samples": len(recent),
                "independent_days": days, "mean_r": round(mean, 6),
                "quarantined": supported and mean <= 0,
                "supported": supported,
            }
        return self

    def assess(self, *, symbol, candidate, quote, risk):
        reasons = []
        spread_fraction = None
        if self.invalid_outcomes:
            reasons.append("INVALID_PAPER_EVIDENCE")
        if not isinstance(risk, dict) or risk.get("approved") is not True:
            reasons.append("SENIOR_RISK_REJECT")
        try:
            bid, ask = float(quote["bid"]), float(quote["ask"])
            entry, stop = float(candidate["entry"]), float(candidate["stop_loss"])
            distance = abs(entry - stop)
            if not all(isfinite(v) and v > 0 for v in (bid, ask, entry, stop, distance)) or ask < bid:
                raise ValueError("Invalid quote or stop")
            spread_fraction = (ask - bid) / distance
            if spread_fraction > self.max_spread_fraction:
                reasons.append("SPREAD_TOO_WIDE")
        except (KeyError, TypeError, ValueError):
            reasons.append("INVALID_QUOTE_OR_STOP")
        pair = self.pairs.get((str(symbol).upper(), str(candidate.get("strategy", "")).upper()))
        if pair and pair["quarantined"]:
            reasons.append("NEGATIVE_PAPER_EXPECTANCY")
        allowed = not reasons
        if allowed:
            reasons.append("PAPER_GATES_PASSED" if pair and pair["supported"] else "COLLECT_FORWARD_EVIDENCE")
        return {
            "agent": "recovery_guardian", "name": self.NAME, "authority": "VETO_ONLY",
            "environment": "PAPER", "broker_execution_allowed": False,
            "allowed": allowed, "reason_codes": reasons,
            "spread_fraction": None if spread_fraction is None else round(spread_fraction, 6),
        }

    def report(self, *, daily_loss_percent, daily_limit_percent, as_of=None, checks=()):
        if not all(isfinite(v) and v >= 0 for v in (daily_loss_percent, daily_limit_percent)) or daily_limit_percent <= 0:
            raise ValueError("Invalid recovery daily limits")
        pairs = [p for p in self.pairs.values() if p["quarantined"]]
        state = ("EVIDENCE_INVALID" if self.invalid_outcomes else
                 "SESSION_HALTED" if daily_loss_percent >= daily_limit_percent else
                 "RECOVERY_FILTERING" if pairs else "COLLECTING_EVIDENCE")
        return {
            "version": 1, "name": self.NAME, "generated_at": self._stamp(as_of or datetime.now(timezone.utc)).isoformat(),
            "environment": "PAPER", "authority": "VETO_ONLY", "broker_execution_allowed": False,
            "state": state, "closed_examples": self.closed_examples,
            "invalid_outcomes": self.invalid_outcomes, "duplicates_ignored": self.duplicates_ignored,
            "excluded_future": self.excluded_future, "daily_loss_percent": round(daily_loss_percent, 4),
            "daily_limit_percent": daily_limit_percent, "max_spread_fraction": self.max_spread_fraction,
            "minimum_samples": self.minimum_samples, "minimum_days": self.minimum_days, "window": self.window,
            "quarantined_pairs": pairs, "checks": list(checks)[-30:],
            "methodology": "Descriptive recent settled Paper R, with spread and without fees. Calendar days are not independent market trials. Passing this veto does not establish a profitable strategy.",
        }

    @staticmethod
    def save_report(report, path):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=target.stem + "-", suffix=".tmp", dir=target.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(report, handle, indent=2, allow_nan=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            for attempt in range(3):
                try:
                    os.replace(temporary, target)
                    break
                except PermissionError:
                    if attempt == 2:
                        raise
                    time.sleep(0.03)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
