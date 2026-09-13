"""Persistent, no-order paper ledger for the ATLAS MT5 monitor.

The ledger models the lifecycle of a trade candidate without calling MT5 order
submission. It is designed for forward-demo validation: entries, stop/target
exits, R-multiple, and risk-normalized P&L remain auditable across restarts.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

if os.name == "nt":
    import msvcrt
else:
    import fcntl


class PaperLedgerError(RuntimeError):
    """Raised when the demo ledger cannot safely process a trade."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MT5PaperLedger:
    """File-backed paper-trade ledger for one or more ATLAS demo workers.

    position_size is the risk-engine size used for simulation only. It is never
    converted into an MT5 lot and this class never communicates with a broker
    order endpoint.
    """

    def __init__(self, path: str | None = None, max_open_positions: int | None = None) -> None:
        configured_path = path or os.getenv("ATLAS_DEMO_LEDGER", "data/atlas_demo_ledger.json")
        self.path = Path(configured_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.path.with_suffix(f"{self.path.suffix}.lock")
        configured_limit = max_open_positions or int(os.getenv("ATLAS_DEMO_MAX_OPEN_POSITIONS", "3"))
        self.max_open_positions = max(1, int(configured_limit))
        self._state = self._load()

    def _load(self) -> dict[str, list[dict[str, Any]]]:
        if not self.path.exists():
            return {"open_positions": [], "closed_trades": []}

        try:
            with self.path.open("r", encoding="utf-8") as handle:
                state = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise PaperLedgerError(f"Cannot read demo ledger {self.path}: {exc}") from exc

        if not isinstance(state, dict):
            raise PaperLedgerError("Demo ledger must contain a JSON object.")

        open_positions = state.get("open_positions", [])
        closed_trades = state.get("closed_trades", [])
        if not isinstance(open_positions, list) or not isinstance(closed_trades, list):
            raise PaperLedgerError("Demo ledger has an invalid trade collection.")
        return {"open_positions": open_positions, "closed_trades": closed_trades}

    @contextmanager
    def _locked_state(self) -> Iterator[None]:
        """Lock the ledger across processes and refresh state before use."""
        try:
            with self.lock_path.open("a+b") as lock_handle:
                if os.name == "nt":
                    lock_handle.seek(0, os.SEEK_END)
                    if lock_handle.tell() == 0:
                        lock_handle.write(b"\0")
                        lock_handle.flush()
                    lock_handle.seek(0)
                    msvcrt.locking(lock_handle.fileno(), msvcrt.LK_LOCK, 1)
                else:
                    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)

                try:
                    self._state = self._load()
                    yield
                finally:
                    if os.name == "nt":
                        lock_handle.seek(0)
                        msvcrt.locking(lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        except OSError as exc:
            raise PaperLedgerError(f"Cannot lock demo ledger {self.path}: {exc}") from exc

    def _persist(self) -> None:
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        try:
            with temporary.open("w", encoding="utf-8") as handle:
                json.dump(self._state, handle, indent=2, sort_keys=True, default=str)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(self.path)
        except OSError as exc:
            raise PaperLedgerError(f"Cannot persist demo ledger {self.path}: {exc}") from exc

    def open_positions(self) -> list[dict[str, Any]]:
        with self._locked_state():
            return [dict(position) for position in self._state["open_positions"]]

    def closed_trades(self) -> list[dict[str, Any]]:
        with self._locked_state():
            return [dict(trade) for trade in self._state["closed_trades"]]

    def has_open_position(self, symbol: str) -> bool:
        normalized = symbol.upper()
        with self._locked_state():
            return any(
                str(position["symbol"]).upper() == normalized
                for position in self._state["open_positions"]
            )

    def open_trade(
        self,
        *,
        symbol: str,
        direction: str,
        entry: float,
        stop_loss: float,
        take_profit: float,
        position_size: float,
        risk: dict[str, Any],
        strategy: str,
        confidence: float,
        timeframe: str,
        decision: dict[str, Any],
    ) -> dict[str, Any]:
        direction = direction.upper()
        if direction not in {"LONG", "SHORT"}:
            raise PaperLedgerError("Paper trade direction must be LONG or SHORT.")

        entry = float(entry)
        stop_loss = float(stop_loss)
        take_profit = float(take_profit)
        position_size = float(position_size)
        if entry <= 0 or stop_loss <= 0 or take_profit <= 0 or position_size <= 0:
            raise PaperLedgerError("Demo trade prices and position size must be positive.")
        if direction == "LONG" and not (stop_loss < entry < take_profit):
            raise PaperLedgerError("LONG demo trade requires SL < entry < TP.")
        if direction == "SHORT" and not (take_profit < entry < stop_loss):
            raise PaperLedgerError("SHORT demo trade requires TP < entry < SL.")

        risk_amount = float(risk.get("actual_risk_amount", risk.get("maximum_risk_amount", 0.0)) or 0.0)
        trade = {
            "id": str(uuid4()),
            "symbol": str(symbol),
            "direction": direction,
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "position_size": position_size,
            "risk_amount": risk_amount,
            "risk_percent": float(risk.get("risk_percent", 0.0) or 0.0),
            "risk_reward": float(risk.get("risk_reward", 0.0) or 0.0),
            "strategy": str(strategy),
            "confidence": float(confidence),
            "timeframe": str(timeframe),
            "decision": dict(decision),
            "status": "OPEN",
            "opened_at": utc_now(),
        }

        normalized = symbol.upper()
        with self._locked_state():
            if any(
                str(position["symbol"]).upper() == normalized
                for position in self._state["open_positions"]
            ):
                raise PaperLedgerError(f"An open demo position already exists for {symbol}.")
            if len(self._state["open_positions"]) >= self.max_open_positions:
                raise PaperLedgerError(
                    f"Maximum open demo positions reached ({self.max_open_positions})."
                )
            self._state["open_positions"].append(trade)
            self._persist()
        return dict(trade)

    def close_due_positions(self, symbol: str, *, bid: float, ask: float) -> list[dict[str, Any]]:
        """Close only positions whose stop or target is reached by the latest quote."""
        normalized = symbol.upper()
        bid = float(bid)
        ask = float(ask)
        if bid <= 0 or ask <= 0 or ask < bid:
            raise PaperLedgerError(f"Invalid quote for {symbol}.")

        with self._locked_state():
            remaining: list[dict[str, Any]] = []
            closed: list[dict[str, Any]] = []
            for position in self._state["open_positions"]:
                if str(position["symbol"]).upper() != normalized:
                    remaining.append(position)
                    continue

                direction = position["direction"]
                exit_price = bid if direction == "LONG" else ask
                reason: str | None = None
                if direction == "LONG":
                    if exit_price <= float(position["stop_loss"]):
                        reason = "STOP_LOSS"
                    elif exit_price >= float(position["take_profit"]):
                        reason = "TAKE_PROFIT"
                else:
                    if exit_price >= float(position["stop_loss"]):
                        reason = "STOP_LOSS"
                    elif exit_price <= float(position["take_profit"]):
                        reason = "TAKE_PROFIT"

                if reason is None:
                    remaining.append(position)
                    continue

                risk_per_unit = abs(float(position["entry"]) - float(position["stop_loss"]))
                movement = (
                    (exit_price - float(position["entry"]))
                    if direction == "LONG"
                    else (float(position["entry"]) - exit_price)
                )
                r_multiple = round(movement / risk_per_unit, 4)
                closed_trade = {
                    **position,
                    "status": "CLOSED",
                    "exit": round(exit_price, 10),
                    "exit_reason": reason,
                    "r_multiple": r_multiple,
                    # The position-size model is instrument-neutral. This value is
                    # explicitly a risk-normalized estimate, not broker P&L.
                    "risk_normalized_pnl": round(
                        r_multiple * float(position["risk_amount"]), 2
                    ),
                    "closed_at": utc_now(),
                }
                closed.append(closed_trade)

            if closed:
                self._state["open_positions"] = remaining
                self._state["closed_trades"].extend(closed)
                self._persist()
            return closed

    def summary(self) -> dict[str, int]:
        with self._locked_state():
            return {
                "open_positions": len(self._state["open_positions"]),
                "closed_trades": len(self._state["closed_trades"]),
                "recorded_trades": len(self._state["open_positions"])
                + len(self._state["closed_trades"]),
            }
