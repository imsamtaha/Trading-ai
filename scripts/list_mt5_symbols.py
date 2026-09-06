from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow `python scripts/list_mt5_symbols.py` from the repository root.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import MetaTrader5 as mt5

from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List relevant symbols available in the connected MT5 terminal"
    )
    parser.add_argument("--limit", type=int, default=2000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    broker = MT5Broker(MT5Config.from_env())
    try:
        account = broker.connect()
        symbols = mt5.symbols_get()
        if symbols is None:
            raise MT5ExecutionError(f"symbols_get failed: {mt5.last_error()}")

        keywords = (
            "EURUSD",
            "XAU",
            "GOLD",
            "XAG",
            "SILVER",
            "GAS",
            "NATGAS",
            "XRP",
            "SOL",
        )
        rows = []
        for symbol in symbols[: args.limit]:
            name = symbol.name
            upper = name.upper()
            if any(keyword in upper for keyword in keywords):
                rows.append(
                    {
                        "name": name,
                        "visible": bool(symbol.visible),
                        "trade_mode": int(symbol.trade_mode),
                        "digits": int(symbol.digits),
                        "point": float(symbol.point),
                        "volume_min": float(symbol.volume_min),
                        "volume_step": float(symbol.volume_step),
                    }
                )

        print(json.dumps({
            "account": {
                "server": account["server"],
                "currency": account["currency"],
            },
            "count": len(rows),
            "symbols": rows,
        }, indent=2))
        return 0
    except MT5ExecutionError as exc:
        print(json.dumps({"status": "MT5_ERROR", "error": str(exc)}, indent=2))
        return 1
    finally:
        broker.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
