from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Callable


class RuntimeControlError(RuntimeError):
    pass


def _state_path() -> Path:
    configured = os.getenv("ATLAS_RUNTIME_STATE_FILE", "").strip()
    if configured:
        return Path(configured)
    return Path(os.getenv("TEMP", ".")) / "atlas_runtime_state.json"


def get_demo_execution_enabled() -> bool:
    path = _state_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return bool(data.get("demo_execution", False))
    except (OSError, ValueError, TypeError):
        return os.getenv("ATLAS_USER_DEMO_ORDERS", "false").lower() == "true"


def set_demo_execution_enabled(enabled: bool) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"demo_execution": bool(enabled)}), encoding="utf-8")


def _default_restart_scheduler() -> None:
    launcher = Path(os.getenv(
        "ATLAS_BACKEND_LAUNCHER",
        r"C:\Users\KHAT W TELEPHONE\ATLAS_Backup\run-atlas-private-api.ps1",
    ))
    if not launcher.exists():
        raise RuntimeControlError("Backend restart launcher is unavailable.")
    escaped = str(launcher).replace("'", "''")
    command = (
        f"Start-Sleep -Milliseconds 900; Stop-Process -Id {os.getpid()} -Force; "
        f"& '{escaped}'"
    )
    flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
    subprocess.Popen(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        creationflags=flags,
        close_fds=True,
    )


class RuntimeControlService:
    def __init__(self, restart_scheduler: Callable[[], None] | None = None) -> None:
        self.restart_scheduler = restart_scheduler or _default_restart_scheduler

    def status(self) -> dict[str, object]:
        launcher = Path(os.getenv(
            "ATLAS_BACKEND_LAUNCHER",
            r"C:\Users\KHAT W TELEPHONE\ATLAS_Backup\run-atlas-private-api.ps1",
        ))
        return {
            "backend": "ONLINE",
            "demo_execution": get_demo_execution_enabled(),
            "live_execution": "LOCKED",
            "restart_supported": launcher.exists(),
        }

    def set_demo_execution(self, enabled: bool) -> dict[str, object]:
        set_demo_execution_enabled(enabled)
        return self.status()

    def restart(self) -> dict[str, str]:
        self.restart_scheduler()
        return {"status": "RESTARTING"}
