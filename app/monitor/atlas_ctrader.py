"""Forward PAPER simulation with view-only cTrader Demo market data."""
from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from websockets.exceptions import WebSocketException

from app.execution.provider_mode import ctrader_selected
from app.integrations.ctrader_demo import DemoConnectionError, authenticated_demo, demo_credentials
from app.integrations.ctrader_market import CTraderDemoMarket
from app.monitor.atlas_mt5 import AtlasPaperMonitor
from scripts.export_owner_paper_snapshot import export_snapshot, write_json_atomic


class AtlasCTraderPaperMonitor(AtlasPaperMonitor):
    """Run the existing analysis, risk, Council and ledger with a cTrader feed."""

    market_source = "CTRADER_DEMO"
    MarketError = DemoConnectionError
    require_council = True
    training_default = "true"
    broker: CTraderDemoMarket

    def __init__(self, *, state_dir: Path, symbols: list[str], **kwargs: Any) -> None:
        if not ctrader_selected():
            raise ValueError("Set ATLAS_BROKER_PROVIDER=ctrader to start the cTrader PAPER worker.")
        if os.getenv("ATLAS_LIVE_TRADING", "false").strip().lower() != "false":
            raise ValueError("The cTrader PAPER worker requires ATLAS_LIVE_TRADING=false.")
        if not symbols:
            raise ValueError("Configure at least one broker-exact cTrader symbol.")
        self.state_dir = state_dir
        super().__init__(symbols=symbols, state_dir=state_dir, **kwargs)
        self.auto_discover = False
        if not math.isfinite(self.account_equity) or self.account_equity <= 0:
            raise ValueError("Set ATLAS_DEMO_ACCOUNT_EQUITY to positive finite simulation equity.")
        if not 50 <= self.candle_limit <= 500:
            raise ValueError("Set ATLAS_CANDLE_LIMIT between 50 and 500.")
        self.signing_key = os.getenv("ATLAS_OWNER_SNAPSHOT_HMAC_KEY", "")
        if self.signing_key and len(self.signing_key) < 32:
            raise ValueError("ATLAS_OWNER_SNAPSHOT_HMAC_KEY must contain at least 32 characters.")

    def _quote_settings(self) -> tuple[int, int]:
        return max(1, int(os.getenv("ATLAS_CTRADER_MAX_QUOTE_AGE_SECONDS", "30"))), 0

    def _market_candles(self, symbol: str) -> list[dict[str, Any]]:
        self.broker.quote(symbol)
        return self.broker.candles(symbol, self.interval, self.candle_limit)

    def _validate_settlement_quote(self, quote: dict[str, Any], position: dict[str, Any]) -> None:
        fresh, reason = self._validate_quote_freshness(quote)
        if not fresh:
            raise DemoConnectionError(reason)
        opened_at = datetime.fromisoformat(position["opened_at"]).timestamp()
        if quote["time_msc"] <= opened_at * 1000:
            raise DemoConnectionError("CTRADER_QUOTE_PRECEDES_PAPER_ENTRY")

    def _record_event(self, event: dict[str, Any]) -> dict[str, Any]:
        return self.journal.append({
            **event, "market_source": self.market_source,
            "execution_environment": "PAPER", "broker_execution_allowed": False,
        })

    def _bind_state_to_account(self, account_id: int) -> None:
        path = self.state_dir / "ctrader_account.json"
        identity = {"market_source": self.market_source, "account_id": account_id}
        if path.exists():
            if json.loads(path.read_text(encoding="utf-8")) != identity:
                raise DemoConnectionError("CTRADER_STATE_BELONGS_TO_ANOTHER_ACCOUNT")
        else:
            if any(path.exists() for path in (
                self.ledger.path, self.journal.path, self.council_training_journal.path,
                self.council_profile_path,
            )):
                raise DemoConnectionError("CTRADER_STATE_HAS_NO_ACCOUNT_BINDING")
            write_json_atomic(path, identity)

    def _publish_status(self, status: str, error: str | None = None, *, bound: bool = False) -> None:
        write_json_atomic(self.state_dir / "atlas_demo_status.json", {
            "status": status, "updated_at": datetime.now(timezone.utc).isoformat(),
            "mode": "CTRADER_DEMO_PAPER", "market_source": self.market_source,
            "cycle_seconds": self.cycle_seconds, "last_error": error,
            "live_execution": False, "broker_execution_allowed": False,
        })
        if self.signing_key and bound:
            export_snapshot(
                self.state_dir, self.state_dir / "atlas_owner_snapshot.json", self.signing_key,
                origin="CTRADER_DEMO_PAPER",
            )

    def run_once(self) -> list[dict[str, Any]]:
        bound = False
        try:
            with authenticated_demo(*demo_credentials()) as (session, account_id):
                self._bind_state_to_account(account_id)
                bound = True
                self.broker = CTraderDemoMarket(session, account_id, self.max_quote_age_seconds)
                tracked = dict.fromkeys([*self.symbols, *(row["symbol"] for row in self.ledger.open_positions())])
                self.broker.subscribe(list(tracked))
                events = self.cycle()
        except DemoConnectionError as exc:
            self._publish_status("ERROR", str(exc), bound=bound)
            raise
        except (OSError, WebSocketException):
            self._publish_status("ERROR", "CTRADER_CONNECTION_FAILED", bound=bound)
            raise DemoConnectionError("CTRADER_CONNECTION_FAILED") from None

        error = next((event for event in events if event["status"].endswith("ERROR")), None)
        self._publish_status("DEGRADED" if error else "CONNECTED", error["reason"] if error else None, bound=True)
        return events
