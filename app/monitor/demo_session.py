"""Single-worker, reconnecting paper session with an atomic public status file."""
from __future__ import annotations

import json
import os
import socket
import time
from datetime import datetime, timezone
from pathlib import Path

from app.monitor.atlas_mt5 import AtlasMT5Monitor


def write_status(status: str, events: list[dict] | None = None) -> None:
    path = Path(os.getenv("ATLAS_DEMO_STATUS", "data/atlas_demo_status.json"))
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"status": status, "updated_at": datetime.now(timezone.utc).isoformat(),
               "mode": "PAPER_DEMO", "live_execution": False,
               "cycle_seconds": max(10, int(os.getenv("ATLAS_CYCLE_SECONDS", "30"))),
               "events": [{"symbol": event.get("symbol"), "status": event.get("status"),
                           "reason": event.get("reason") if event.get("status") not in {"ERROR", "MT5_ERROR"}
                           else "Market data or analysis unavailable."}
                          for event in (events or [])]}
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    from dotenv import load_dotenv
    load_dotenv(override=False)
    if os.getenv("ATLAS_LIVE_TRADING", "false").lower() != "false":
        raise ValueError("Demo session refuses live execution configuration.")
    os.environ["MT5_REQUIRE_DEMO"] = "true"
    os.environ["ATLAS_DASHBOARD_ONLY"] = "true"
    os.environ["ATLAS_AGENT_PAPER_EXECUTION_ENABLED"] = "false"
    # Binding is held for the worker lifetime and released on process exit.
    with socket.socket() as lock:
        lock.bind(("127.0.0.1", int(os.getenv("ATLAS_DEMO_LOCK_PORT", "18765"))))
        write_status("STARTING")
        try:
            while True:
                try:
                    symbols = [s.strip() for s in os.getenv("ATLAS_SYMBOLS", "EURUSD").split(",") if s.strip()]
                    monitor = AtlasMT5Monitor(symbols=symbols,
                        interval=os.getenv("ATLAS_INTERVAL", "5m"),
                        candle_limit=int(os.getenv("ATLAS_CANDLE_LIMIT", "200")))
                    events = monitor.run_once()
                    write_status("DEGRADED" if any(e["status"] in {"ERROR", "MT5_ERROR"} for e in events) else "RUNNING", events)
                except Exception:
                    # Retry connection without publishing account details or provider errors.
                    write_status("UNAVAILABLE")
                time.sleep(max(10, int(os.getenv("ATLAS_CYCLE_SECONDS", "30"))))
        finally:
            write_status("STOPPED")


if __name__ == "__main__":
    main()
