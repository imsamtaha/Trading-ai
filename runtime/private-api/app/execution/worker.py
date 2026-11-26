from __future__ import annotations

import logging
import os
import time

from app.execution.atlas import AtlasExecutionService, ExecutionPolicy
from app.execution.heartbeat import AtlasHeartbeat
from app.execution.mt5 import MT5Broker

LOG = logging.getLogger("atlas.mt5.worker")

TIMEFRAMES = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
}


class AtlasMT5Worker:
    """Persistent Windows worker for ATLAS <-> MT5 connectivity.

    It intentionally does not place orders by itself. Trading decisions remain
    owned by the ATLAS monitor/execution service.
    """

    def __init__(self) -> None:
        broker = MT5Broker()
        self.broker = broker
        self.heartbeat = AtlasHeartbeat(broker)
        self.execution = AtlasExecutionService(
            broker=broker,
            policy=ExecutionPolicy(enabled=False),
        )
        self.interval = max(10, int(os.getenv("ATLAS_HEARTBEAT_SECONDS", "30")))

    def run(self) -> None:
        LOG.info("ATLAS MT5 worker starting; heartbeat=%ss", self.interval)
        while True:
            result = self.heartbeat.heartbeat()
            if result["status"] == "connected":
                account = result["account"]
                LOG.info(
                    "MT5 ONLINE server=%s login=%s equity=%s dry_run=%s",
                    account.get("server"),
                    account.get("login"),
                    account.get("equity"),
                    self.broker.config.dry_run,
                )
            else:
                LOG.error("MT5 OFFLINE: %s", result.get("error"))
            time.sleep(self.interval)


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    AtlasMT5Worker().run()
