"""ATLAS MT5 forward-demo runner.

This entry point only records paper trades. It refuses to start if live trading is
enabled and it never sends MetaTrader 5 orders.
"""

from __future__ import annotations

import argparse
import json
import os

from dotenv import load_dotenv

load_dotenv(override=False)

from app.monitor.atlas_mt5 import AtlasMT5Monitor
from app.monitor.runtime import MonitorAlreadyRunning, monitor_lock, operational_log, write_health


def _symbols(value: str | None) -> list[str] | None:
    if not value:
        return None
    symbols = [item.strip() for item in value.split(",") if item.strip()]
    return symbols or None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the ATLAS MT5 forward-demo monitor.")
    parser.add_argument(
        "--symbols",
        default=os.getenv("ATLAS_SYMBOLS"),
        help="Optional comma-separated, broker-exact symbols. Omit to use preferred discovery.",
    )
    parser.add_argument("--interval", default=os.getenv("ATLAS_INTERVAL", "5m"))
    parser.add_argument("--cycle-seconds", type=int, default=int(os.getenv("ATLAS_CYCLE_SECONDS", "30")))
    parser.add_argument("--top-n", type=int, default=int(os.getenv("ATLAS_MONITOR_TOP_N", "12")))
    parser.add_argument("--once", action="store_true", help="Run one connected analysis cycle, then exit.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        with monitor_lock(), operational_log() as logger:
            write_health("STARTING")
            try:
                return _run(args)
            except Exception:
                write_health("FAILED")
                logger.exception("Paper worker failed; ledger retained")
                raise
            finally:
                logger.info("Paper worker exited")
    except MonitorAlreadyRunning as exc:
        print(str(exc))
        return 3


def _run(args: argparse.Namespace) -> int:
    monitor = AtlasMT5Monitor(
        symbols=_symbols(args.symbols),
        interval=args.interval,
        candle_limit=int(os.getenv("ATLAS_CANDLE_LIMIT", "200")),
        cycle_seconds=args.cycle_seconds,
        top_n=args.top_n,
    )
    if args.once:
        print(json.dumps(monitor.run_once(), indent=2, default=str))
        write_health("STOPPED")
        return 0

    monitor.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
