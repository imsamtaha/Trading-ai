from __future__ import annotations
import json
import os
import time
from datetime import datetime
from pathlib import Path

def read_server_health(path: Path | None = None, now: float | None = None) -> dict:
    path = path or Path(os.getenv("ATLAS_SUPERVISOR_STATUS_FILE",
        str(Path.home() / "ATLAS_Backup" / "server" / "status.json")))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        checked = str(data["checked_at_utc"])
        stamp = datetime.fromisoformat(checked.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            return {"state": "UNAVAILABLE"}
        age = (time.time() if now is None else now) - stamp.timestamp()
        components = {}
        for name in ("backend", "frontend", "public_route", "mt5"):
            item = data.get("components", {}).get(name, {})
            if isinstance(item, dict) and isinstance(item.get("state"), str):
                clean = {"state": item["state"][:64]}
                count = item.get("open_positions")
                if name == "mt5" and isinstance(count, int) and count >= 0:
                    clean["open_positions"] = count
                components[name] = clean
        return {"state": "ACTIVE" if 0 <= age <= 180 else "STALE",
                "checked_at_utc": checked, "components": components}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {"state": "UNAVAILABLE"}
