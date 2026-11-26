"""Run the ATLAS cTrader Demo PAPER worker on the private runtime host."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from filelock import FileLock, Timeout

from app.integrations.ctrader_demo import DemoConnectionError, demo_credentials
from app.monitor.atlas_ctrader import AtlasCTraderPaperMonitor
from app.paper_trading.mt5_ledger import PaperLedgerError


def main() -> int:
    load_dotenv(override=False)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Run one demo market-data cycle and exit.")
    parser.add_argument("--state-dir", type=Path, default=os.getenv("ATLAS_CTRADER_STATE_DIR", "data/ctrader"))
    parser.add_argument("--symbols", default=os.getenv("ATLAS_CTRADER_SYMBOLS", "EURUSD"))
    parser.add_argument("--interval", default=os.getenv("ATLAS_INTERVAL", "5m"))
    args = parser.parse_args()
    symbols = list(dict.fromkeys(name.strip() for name in args.symbols.split(",") if name.strip()))

    try:
        demo_credentials()
        state_dir = args.state_dir.expanduser().resolve()
        state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        with FileLock(state_dir / "paper-worker.lock", timeout=0):
            monitor = AtlasCTraderPaperMonitor(
                state_dir=state_dir, symbols=symbols, interval=args.interval,
                cycle_seconds=int(os.getenv("ATLAS_CYCLE_SECONDS", "30")),
                candle_limit=int(os.getenv("ATLAS_CANDLE_LIMIT", "200")),
            )
            # Retry market interruptions in continuous mode. CLI output is
            # limited to statuses while detailed evidence stays in local files.
            while True:
                try:
                    events = monitor.run_once()
                except DemoConnectionError as exc:
                    print(f"cTrader Demo PAPER cycle unavailable ({exc})", file=sys.stderr, flush=True)
                    if args.once:
                        return 2
                else:
                    counts: dict[str, int] = {}
                    for event in events:
                        status = event["status"]
                        counts[status] = counts.get(status, 0) + 1
                    print(json.dumps({"mode": "CTRADER_DEMO_PAPER", "events": counts}), flush=True)
                    if args.once:
                        return 2 if any(status.endswith("ERROR") for status in counts) else 0
                time.sleep(monitor.cycle_seconds)
    except Timeout:
        print("A cTrader PAPER worker already owns this state directory.", file=sys.stderr)
        return 2
    except (DemoConnectionError, PaperLedgerError, OSError, ValueError) as exc:
        print(f"cTrader PAPER worker stopped ({exc})", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
