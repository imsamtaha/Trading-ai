"""Forced-safe EURUSD execution-path check.

This script validates ATLAS -> execution gate -> MT5 adapter without sending an
order. It forces dry-run mode in-process and additionally refuses to continue
unless the connected MT5 server identifies itself as a demo environment.

The SL/TP values are synthetic validation bounds, not trading advice.
"""
from __future__ import annotations

import os

# Hard safety locks. Shell values cannot override these for this script.
os.environ["ATLAS_LIVE_TRADING"] = "false"
os.environ["ATLAS_DASHBOARD_ONLY"] = "true"

from app.execution.atlas import AtlasExecutionService, ExecutionPolicy
from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError


def main() -> int:
    config = MT5Config.from_env()
    if not config.dry_run:
        raise RuntimeError("Safety check failed: MT5Config is not dry-run.")

    broker = MT5Broker(config)
    service = AtlasExecutionService(
        broker=broker,
        policy=ExecutionPolicy(
            enabled=True,  # enables only the simulated gateway below
            min_confidence=55.0,
            max_risk_level="MEDIUM",
            allow_buy=True,
            allow_sell=True,
        ),
    )

    try:
        account = broker.connect()
        server = str(account.get("server", ""))
        if "demo" not in server.lower():
            raise RuntimeError(
                "Safety check failed: connected MT5 server is not identified as DEMO."
            )

        quote = broker.quote("EURUSD")
        ask = float(quote["ask"])
        point = float(quote["point"])

        # Synthetic bounds used only to validate request construction.
        stop_loss = ask - (100 * point)
        take_profit = ask + (100 * point)

        result = service.execute(
            symbol="EURUSD",
            decision={
                "decision": "BUY",
                "confidence": 60.0,
                "risk_level": "LOW",
            },
            volume=0.01,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        if result.get("status") != "DRY_RUN":
            raise RuntimeError(f"Expected DRY_RUN, received: {result}")

        print("EURUSD DRY-RUN: PASS")
        print(f"server={server}")
        print(f"symbol={result['symbol']}")
        print(f"side={result['side']}")
        print(f"status={result['status']}")
        print("live_order_sent=false")
        return 0
    except MT5ExecutionError as exc:
        print(f"EURUSD DRY-RUN: FAIL: {exc}")
        return 1
    finally:
        broker.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
