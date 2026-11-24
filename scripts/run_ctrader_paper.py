"""Run the ATLAS cTrader demo bridge on Ubuntu with a local PAPER ledger."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import BinaryIO

from dotenv import load_dotenv

from app.execution.provider_mode import ctrader_selected
from app.integrations.ctrader_demo import DemoConnectionError, DemoCredentials
from app.integrations.ctrader_market import MAX_CANDLES, PERIODS, CTraderMarketData
from app.monitor.atlas_mt5 import AtlasMT5Monitor


def _export_candles(destination: Path, candles: list[dict]) -> None:
    if len(candles) < 110:
        raise DemoConnectionError("INSUFFICIENT_HISTORY_FOR_TRAINING_EXPORT")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=destination.parent,
                                prefix=".candles-", delete=False) as handle:
            temporary = Path(handle.name)
            writer = csv.writer(handle)
            writer.writerow(("time", "open", "high", "low", "close"))
            for candle in candles:
                timestamp = datetime.fromtimestamp(candle["open_time"] / 1000, timezone.utc)
                writer.writerow((timestamp.isoformat(), *(candle[key] for key in ("open", "high", "low", "close"))))
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _lock_worker(handle: BinaryIO) -> None:
    try:
        if os.name == "nt":
            import msvcrt

            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        raise DemoConnectionError("PAPER_WORKER_LOCK_UNAVAILABLE") from None


def main(argv: list[str] | None = None) -> int:
    load_dotenv(override=False)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", default=os.getenv("ATLAS_CTRADER_SYMBOLS") or "XAUUSD",
                        help="Comma-separated cTrader platform symbol names")
    parser.add_argument("--interval", choices=PERIODS, default="5m")
    parser.add_argument("--candles", type=int, choices=range(50, MAX_CANDLES + 1),
                        default=200, metavar="50-500")
    parser.add_argument("--cycle-seconds", type=int, default=30)
    parser.add_argument("--state-dir", type=Path, default=Path("data/ctrader"))
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="Check account and market data with no ledger writes")
    action.add_argument("--export-candles", type=Path, help="Write training OHLC for one symbol to a new CSV")
    action.add_argument("--once", action="store_true", help="Run one PAPER cycle")
    args = parser.parse_args(argv)
    symbols = list(dict.fromkeys(symbol.strip() for symbol in args.symbols.split(",") if symbol.strip()))
    if not 1 <= len(symbols) <= 12:
        parser.error("Choose between 1 and 12 cTrader symbols.")
    if (args.check or args.export_candles) and len(symbols) != 1:
        parser.error("Choose one symbol for a check or training export.")

    market = CTraderMarketData()
    try:
        if not ctrader_selected():
            raise DemoConnectionError("CTRADER_PROVIDER_NOT_SELECTED")
        if os.getenv("ATLAS_LIVE_TRADING", "false").strip().lower() != "false":
            raise DemoConnectionError("PAPER_REQUIRES_LIVE_TRADING_FALSE")
        DemoCredentials.from_env()

        if args.check or args.export_candles:
            try:
                market.connect()
                candles = market.candles(symbols[0], args.interval, args.candles)
                if args.export_candles:
                    _export_candles(args.export_candles, candles)
                else:
                    if len(candles) < 50:
                        raise DemoConnectionError("INSUFFICIENT_CANDLE_HISTORY")
                    market.quote(symbols[0])
                print(json.dumps({"status": "CONNECTED", "source": "CTRADER_DEMO",
                                  "access": "VIEW_ONLY", "symbol": symbols[0], "closed_candles": len(candles),
                                  "checked_at": datetime.now(timezone.utc).isoformat()}))
                return 0
            finally:
                market.disconnect()

        args.state_dir.mkdir(parents=True, exist_ok=True)
        with (args.state_dir / "worker.lock").open("a+b") as lock:
            _lock_worker(lock)
            monitor = AtlasMT5Monitor(
                symbols=symbols, interval=args.interval, candle_limit=args.candles,
                cycle_seconds=args.cycle_seconds, market_data=market, state_dir=args.state_dir,
            )
            if args.once:
                events = monitor.run_once()
                counts = dict(Counter(event["status"] for event in events))
                print(json.dumps({"status": "PAPER_CYCLE_COMPLETED", "source": "CTRADER_DEMO",
                                  "broker_execution_allowed": False, "events": counts}))
                return 1 if any(status.endswith("ERROR") for status in counts) else 0
            monitor.run_forever()
    except (DemoConnectionError, OSError, ValueError) as exc:
        reason = str(exc) if isinstance(exc, DemoConnectionError) else type(exc).__name__
        print(json.dumps({"status": "UNAVAILABLE", "source": "CTRADER_DEMO", "reason": reason}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    os.umask(0o077)
    raise SystemExit(main())
