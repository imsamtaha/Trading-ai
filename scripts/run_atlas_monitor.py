from __future__ import annotations

import argparse
import json
import logging
import time

from scripts.atlas_mt5_cycle import analyze_timeframe, build_decision, TIMEFRAMES
from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError
from app.intelligence.journal import SignalJournal

LOG = logging.getLogger("atlas.monitor")


def main() -> int:
    parser = argparse.ArgumentParser(description="Continuous ATLAS MT5 dry-run monitor")
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--interval", type=int, default=300, help="seconds between cycles")
    parser.add_argument("--count", type=int, default=200)
    args = parser.parse_args()

    broker = MT5Broker(MT5Config.from_env())
    journal = SignalJournal()

    try:
        while True:
            account = broker.connect()
            results = {
                timeframe: analyze_timeframe(broker, args.symbol, mt5_timeframe, args.count)
                for timeframe, mt5_timeframe in TIMEFRAMES.items()
            }
            decision = build_decision(results)
            record = journal.append({
                "mode": "DRY_RUN" if broker.config.dry_run else "LIVE_GATEWAY",
                "symbol": args.symbol,
                "server": account["server"],
                "login": account["login"],
                "equity": account["equity"],
                "decision": decision,
            })
            LOG.info(
                "%s decision=%s score=%s confidence=%s risk=%s journal_count=%s",
                args.symbol,
                decision["decision"],
                decision["score"],
                decision["confidence"],
                decision["risk_level"],
                journal.count(),
            )
            broker.disconnect()
            time.sleep(max(30, args.interval))
    except KeyboardInterrupt:
        LOG.info("ATLAS monitor stopped")
        return 0
    except MT5ExecutionError as exc:
        LOG.error("ATLAS cycle failed: %s", exc)
        return 1
    finally:
        broker.disconnect()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    raise SystemExit(main())
