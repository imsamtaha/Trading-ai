"""Local paper worker ownership, health, and bounded operational logs."""
from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path


class MonitorAlreadyRunning(RuntimeError):
    pass


def runtime_path(suffix: str) -> Path:
    # Key ownership and health to the canonical ledger, including relative paths.
    ledger = Path(os.getenv("ATLAS_DEMO_LEDGER", "data/atlas_demo_ledger.json")).resolve()
    return ledger.with_name(ledger.name + suffix)


@contextmanager
def monitor_lock():
    """Hold an OS lock for the worker lifetime; crashes release it automatically.

    Never unlink this file: replacing a lock inode could permit two owners.
    This protects runners using this entry point; older/manual workers must be
    stopped before rollout.
    """
    path = runtime_path(".monitor.lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        if os.name == "nt":
            import msvcrt
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise MonitorAlreadyRunning("A paper monitor already owns this ledger.") from exc
        else:
            import fcntl
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise MonitorAlreadyRunning("A paper monitor already owns this ledger.") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def write_health(status: str, *, events: int = 0) -> None:
    path = runtime_path(".health.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "pid": os.getpid(), "status": status, "events": events,
        "environment": "PAPER", "broker_execution_allowed": False,
    }
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


@contextmanager
def operational_log():
    """Rotate only operational summaries; never delete/rotate training or trades."""
    path = runtime_path(".monitor.log")
    path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("atlas.paper.monitor")
    handler = RotatingFileHandler(path, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        yield logger
    finally:
        logger.removeHandler(handler)
        handler.close()
