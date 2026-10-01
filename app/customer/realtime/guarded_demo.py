"""Final execution gate for the owner's FxPro MT5 demo account."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
from typing import Any

from app.execution.mt5 import MT5Broker, MT5ExecutionError, mt5


class GuardedDemoBroker(MT5Broker):
    def __init__(self, config, *, login: int, server: str,
                 max_volume: float = 0.01, max_risk_pct: float = 0.1,
                 state_path: Path | None = None):
        super().__init__(config)
        self.login = int(login)
        self.server = server
        self.max_volume = max_volume
        self.max_risk_pct = max_risk_pct
        self.state_path = Path(state_path) if state_path else None

    def connect(self) -> dict[str, Any]:
        account = super().connect()
        try:
            self._identity(mt5.account_info())
        except Exception:
            self.disconnect()
            raise
        return account

    def _identity(self, account: Any) -> None:
        if (account is None or int(account.login) != self.login
                or str(account.server) != self.server
                or int(account.trade_mode) != int(mt5.ACCOUNT_TRADE_MODE_DEMO)):
            raise MT5ExecutionError("Expected FxPro demo account is not active.")
    def _pre_send(self, request: dict[str, Any], account: Any) -> None:
        self._identity(account)
        terminal = mt5.terminal_info()
        if (terminal is None or not bool(terminal.trade_allowed)
                or bool(getattr(terminal, "tradeapi_disabled", False))
                or not bool(account.trade_allowed)
                or not bool(getattr(account, "trade_expert", True))):
            raise MT5ExecutionError("MT5 automated trading is disabled.")
        volume = float(request["volume"])
        if not (0 < volume <= self.max_volume + 1e-8):
            raise MT5ExecutionError("Demo volume exceeds the fixed cap.")
        positions = mt5.positions_get()
        if positions is None or len(positions) != 0:
            raise MT5ExecutionError("Open position exists or positions unavailable.")
        info = mt5.symbol_info(request["symbol"])
        tick = mt5.symbol_info_tick(request["symbol"])
        if info is None or tick is None or not info.visible:
            raise MT5ExecutionError("Fresh visible symbol quote is required.")
        bid, ask = float(tick.bid), float(tick.ask)
        if not (isfinite(bid) and isfinite(ask) and 0 < bid < ask):
            raise MT5ExecutionError("Invalid broker quote.")
        offset = int(os.getenv("ATLAS_MT5_TICK_OFFSET_SECONDS", "0"))
        if offset not in {0, 7200, 10800} or abs(time.time() - (float(tick.time) - offset)) > 120:
            raise MT5ExecutionError("Broker quote timestamp is stale or in the future.")
        spread_points = (ask - bid) / float(info.point)
        if not (isfinite(spread_points) and spread_points <= 30):
            raise MT5ExecutionError("Spread exceeds demo cap.")
        buy = request["type"] == mt5.ORDER_TYPE_BUY
        price = ask if buy else bid
        sl, tp = float(request["sl"]), float(request["tp"])
        min_stop = max(float(getattr(info, "trade_stops_level", 0) or 0),
                       float(getattr(info, "trade_freeze_level", 0) or 0)) * float(info.point)
        if ((buy and not (sl < price - min_stop and tp > price + min_stop))
                or (not buy and not (tp < price - min_stop and sl > price + min_stop))):
            raise MT5ExecutionError("Stop or target violates broker distances.")
        if abs(float(request["price"]) - price) > 20 * float(info.point):
            raise MT5ExecutionError("Price moved beyond deviation.")
        pnl = mt5.order_calc_profit(request["type"], request["symbol"],
                                    volume, price, sl)
        equity = float(account.equity)
        if (pnl is None or not isfinite(float(pnl)) or float(pnl) >= 0
                or not isfinite(equity) or equity <= 0
                or -float(pnl) > equity * self.max_risk_pct / 100):
            raise MT5ExecutionError("Cash loss at stop exceeds demo risk cap.")
        check = mt5.order_check(request)
        if check is None or int(check.retcode) not in {0, int(mt5.TRADE_RETCODE_DONE)}:
            code = getattr(check, "retcode", None)
            comment = getattr(check, "comment", str(mt5.last_error()) if check is None else "no broker response")
            raise MT5ExecutionError(f"MT5 order_check rejected the order: {code} {comment}")
        self._claim_daily_slot(equity)

    def _claim_daily_slot(self, equity: float) -> None:
        if self.state_path is None:
            raise MT5ExecutionError("Demo daily state path is required.")
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        day = datetime.now(timezone.utc).date().isoformat()
        if self.state_path.exists():
            state = json.loads(self.state_path.read_text(encoding="utf-8"))
            if int(state.get("account_id", 0)) != self.login:
                raise MT5ExecutionError("Demo state belongs to another account.")
        else:
            state = {"account_id": self.login}
        if state.get("day") != day:
            state.update(day=day, baseline_equity=equity, entries=0)
        baseline = float(state["baseline_equity"])
        if baseline <= 0 or equity <= baseline * 0.97 or int(state["entries"]) >= 1:
            raise MT5ExecutionError("Daily demo loss or entry limit reached.")
        state["entries"] += 1
        self.state_path.write_text(json.dumps(state), encoding="utf-8")
