"""Print the ATLAS forward-demo ledger and live-review readiness."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(override=False)

from app.paper_trading.mt5_ledger import MT5PaperLedger
from app.paper_trading.readiness import evaluate_demo_readiness


def main() -> int:
    ledger_path = Path(os.getenv("ATLAS_DEMO_LEDGER", "data/atlas_demo_ledger.json"))
    if not ledger_path.exists():
        print(json.dumps({
            "mode": "PAPER_DEMO", "status": "LEDGER_NOT_FOUND",
            "ledger": str(ledger_path.resolve()), "summary": None,
            "reason": "No ledger available; trade count is unknown.",
        }, indent=2))
        return 2
    ledger = MT5PaperLedger(str(ledger_path))
    report = {
        "mode": "PAPER_DEMO",
        "ledger": str(ledger_path.resolve()),
        "summary": ledger.summary(),
        "readiness": evaluate_demo_readiness(ledger.closed_trades()),
    }
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

