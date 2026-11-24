"""Check a view-only cTrader demo account without starting a trading worker."""

import argparse
import json
import os
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()

    try:
        from dotenv import load_dotenv
        from app.integrations.ctrader_demo import read_demo_account
    except ImportError:
        parser.exit(2, "Install the cTrader check dependencies with: "
                    "python3 -m pip install python-dotenv 'websockets>=12,<18'\n")

    load_dotenv(Path(__file__).resolve().with_name(".env"), override=False)
    # This entry point explicitly selects cTrader for its own process.
    os.environ["ATLAS_BROKER_PROVIDER"] = "ctrader"
    result = read_demo_account()
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "CONNECTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
