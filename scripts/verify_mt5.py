from pathlib import Path
import sys

# Allow `python scripts/verify_mt5.py` from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.execution.heartbeat import AtlasHeartbeat


if __name__ == "__main__":
    result = AtlasHeartbeat().heartbeat()
    print("ATLAS MT5 CONNECTION")
    print("=" * 40)
    print(f"Status: {result['status']}")
    if result["status"] == "connected":
        for key, value in result["account"].items():
            print(f"{key}: {value}")
    else:
        print(f"Error: {result.get('error')}")
