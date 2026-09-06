from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError
from app.intelligence.confidence import SignalQualityEngine
from app.integrations.supabase_journal import SupabaseJournalError, SupabaseSignalJournal
from scripts.atlas_mt5_cycle import TIMEFRAMES, analyze_timeframe, build_decision

LOG = logging.getLogger("atlas.universe")

DEFAULT_SYMBOLS = ["GOLD", "NAT.GAS", "SILVER", "EURUSD", "XRP", "SOLANA"]


def main() -> int:
    parser = argparse.ArgumentParser(description="ATLAS multi-symbol MT5 dry-run monitor")
    parser.add_argument("--symbols", nargs="+", default=DEFAULT_SYMBOLS)
    parser.add_argument("--interval", type=int, default=300)
    parser.add_argument("--count", type=int, default=200)
    args = parser.parse_args()

    broker = MT5Broker(MT5Config.from_env())
    quality_engine = SignalQualityEngine()

    try:
        journal = SupabaseSignalJournal()
    except SupabaseJournalError as exc:
        LOG.error("Supabase journal unavailable: %s", exc)
        return 2

    while True:
        try:
            account = broker.connect()
            for symbol in args.symbols:
                try:
                    broker.symbol_info(symbol)
                    results = {
                        timeframe: analyze_timeframe(
                            broker, symbol, mt5_timeframe, args.count
                        )
                        for timeframe, mt5_timeframe in TIMEFRAMES.items()
                    }
                    decision = build_decision(results)
                    quality = quality_engine.evaluate(
                        decision, decision.get("mtf_alignment", "UNKNOWN")
                    )
                    decision["signal_quality_metrics"] = quality
                    record = journal.record_analysis(
                        symbol=symbol,
                        server=account["server"],
                        login=account["login"],
                        equity=account["equity"],
                        decision=decision,
                    )
                    LOG.info(
                        "%s decision=%s score=%s exec_conf=%s quality=%s journal_id=%s",
                        symbol,
                        decision["decision"],
                        decision["score"],
                        quality["execution_confidence"],
                        quality["signal_quality"],
                        record.get("id"),
                    )
                except MT5ExecutionError as exc:
                    LOG.error("%s analysis failed: %s", symbol, exc)
                except SupabaseJournalError as exc:
                    LOG.error("%s persistence failed: %s", symbol, exc)
            broker.disconnect()
            time.sleep(max(30, args.interval))
        except KeyboardInterrupt:
            LOG.info("ATLAS universe monitor stopped")
            return 0
        except MT5ExecutionError as exc:
            LOG.error("MT5 connection/cycle failed: %s", exc)
            broker.disconnect()
            time.sleep(30)
