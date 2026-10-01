"""One periodic, owner-only learned-council cycle on the FxPro Demo terminal."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.customer.realtime.guarded_demo import GuardedDemoBroker
from app.customer.realtime.learning import LearningLedger
from app.customer.realtime.runtime import MT5DemoRuntime
from app.execution.mt5 import MT5Config, MT5ExecutionError, mt5

LOGIN = 592031391
SERVER = "FxPro-MT5 Demo"
TERMINAL = r"C:\Program Files\MetaTrader 5\terminal64.exe"
STATE_DIR = Path(os.getenv("ATLAS_LEARNED_STATE_DIR", str(ROOT / "var")))
LEDGER = STATE_DIR / "demo_learning.json"
DAILY = STATE_DIR / "demo_daily.json"
MAGIC = 261001


def broker_factory():
    config = replace(MT5Config.from_env(), terminal_path=TERMINAL,
                     login=LOGIN, server=SERVER, magic=MAGIC, dry_run=False)
    return GuardedDemoBroker(config, login=LOGIN, server=SERVER,
                             state_path=DAILY, max_daily_entries=10)
def settle_closed(ledger: LearningLedger) -> None:
    if not ledger.pending_tickets():
        return
    broker = broker_factory()
    try:
        broker.connect()
        for ticket in ledger.pending_tickets():
            positions = mt5.positions_get(ticket=ticket)
            if positions is None or positions:
                continue
            deals = mt5.history_deals_get(position=ticket)
            if not deals or not any(
                int(d.entry) in {int(mt5.DEAL_ENTRY_OUT),
                                 int(getattr(mt5, "DEAL_ENTRY_OUT_BY", -1))}
                for d in deals
            ):
                continue
            pnl = sum(float(d.profit) + float(d.swap) + float(d.commission)
                      + float(getattr(d, "fee", 0.0)) for d in deals)
            ledger.settle(ticket, pnl)
    finally:
        broker.disconnect()


def run() -> dict:
    runtime_path = Path(os.getenv("ATLAS_RUNTIME_STATE_FILE", str(Path(os.getenv("TEMP", ".")) / "atlas_runtime_state.json")))
    try:
        switches = json.loads(runtime_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        switches = {}
    if not (switches.get("demo_execution") is True and switches.get("learned_council_enabled") is True):
        raise MT5ExecutionError("Owner Demo execution and learned council must both be enabled.")
    if os.getenv("ATLAS_MT5_TICK_OFFSET_SECONDS") != "10800":
        raise MT5ExecutionError("FxPro demo clock offset is not configured.")
    ledger = LearningLedger(LEDGER, account_id=str(LOGIN))
    settle_closed(ledger)
    result = MT5DemoRuntime(broker_factory).run(
        customer_id="owner", account_id=str(LOGIN), symbol="EURUSD",
        timeframe="15m", demo_volume=0.01, requested_risk_pct=0.1,
        learned_weights=ledger.weights(),
    )
    if result.get("status") == "EXECUTED":
        execution = result.get("execution") or {}
        ticket = (execution.get("broker_result") or {}).get("ticket")
        if not ticket:
            raise MT5ExecutionError("Executed Demo order has no ticket for learning.")
        ledger.record(int(ticket), str(result["decision"]),
                      dict(result["agent_signals"]))
    print(json.dumps({
        "status": result.get("status"), "reason": result.get("reason"),
        "decision": result.get("decision"), "trace_id": result.get("trace_id"),
        "ticket": ((result.get("execution") or {}).get("broker_result") or {}).get("ticket"),
        "learned_agents": list(ledger.weights()), "pending": ledger.pending_tickets(),
    }, ensure_ascii=False))
    return result


if __name__ == "__main__":
    try:
        run()
    except MT5ExecutionError as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False))
