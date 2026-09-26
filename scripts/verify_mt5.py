from pathlib import Path
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
# Allow python scripts/verify_mt5.py from the repository root.
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env", override=False)
load_dotenv(ROOT / ".env.local", override=False)

from app.execution.heartbeat import AtlasHeartbeat


if __name__ == "__main__":
    result = AtlasHeartbeat().heartbeat()
    print("ATLAS MT5 CONNECTION")
    print("=" * 40)
    print(f"Status: {result['status']}")
    if result["status"] == "connected":
        for key, value in result["account"].items():
            print(f"{key}: {value}")
        raise SystemExit(0)

    print(f"Error: {result.get('error')}")
    raise SystemExit(1)
