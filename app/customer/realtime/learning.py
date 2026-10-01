"""Closed Demo outcomes adjust bounded council weights; no MT5 access here."""
from __future__ import annotations

import json
import os
from pathlib import Path

from app.evolution.engine import EvolutionEngine
from app.evolution.models import AgentMetrics


class LearningLedger:
    def __init__(self, path: Path, *, account_id: str, minimum_samples: int = 10):
        self.path = Path(path)
        self.account_id = str(account_id)
        self.minimum_samples = minimum_samples
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
            if self.data.get("account_id") != self.account_id or self.data.get("version") != 1:
                raise ValueError("Learning ledger belongs to a different account or version")
        else:
            self.data = {"version": 1, "account_id": self.account_id,
                         "pending": {}, "settled": [], "agents": {}}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        payload = json.dumps(self.data, sort_keys=True)
        temporary.write_text(payload, encoding="utf-8")
        try:
            os.replace(temporary, self.path)
        except PermissionError:
            # Some Windows folders permit writes but deny replacing an existing file.
            self.path.write_text(payload, encoding="utf-8")
            temporary.unlink(missing_ok=True)

    def record(self, ticket: int, direction: str, signals: dict[str, str]) -> None:
        key = str(ticket)
        if key in self.data["pending"] or key in self.data["settled"]:
            raise ValueError("Demo ticket already recorded")
        if direction not in {"BUY", "SELL"} or not signals:
            raise ValueError("A directional council decision is required")
        self.data["pending"][key] = {"direction": direction, "signals": dict(signals)}
        self._save()

    def settle(self, ticket: int, pnl: float) -> bool:
        key = str(ticket)
        if key in self.data["settled"]:
            return False
        pending = self.data["pending"].pop(key, None)
        if pending is None:
            return False
        if pnl != 0:
            winner = "LONG" if (pending["direction"] == "BUY") == (pnl > 0) else "SHORT"
            for agent, signal in pending["signals"].items():
                if signal not in {"LONG", "SHORT"}:
                    continue
                item = self.data["agents"].setdefault(agent, {"correct": 0, "total": 0})
                item["total"] += 1
                item["correct"] += int(signal == winner)
        self.data["settled"].append(key)
        self._save()
        return True
    def samples(self, agent: str) -> int:
        return int(self.data["agents"].get(agent, {}).get("total", 0))

    def pending_tickets(self) -> list[int]:
        return [int(ticket) for ticket in self.data["pending"]]

    def weights(self) -> dict[str, float]:
        engine = EvolutionEngine()
        for agent, item in self.data["agents"].items():
            if item["total"] < self.minimum_samples:
                continue
            accuracy = item["correct"] / item["total"]
            engine.record(agent, AgentMetrics(
                risk_adjusted_return=accuracy,
                directional_accuracy=accuracy,
                calibration=accuracy,
                drawdown_control=accuracy,
                regime_accuracy=accuracy,
                consistency=accuracy,
            ))
        return dict(engine.agent_weights)
