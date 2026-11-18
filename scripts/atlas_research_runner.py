"""Resource-gated daily ATLAS scikit-learn / MLflow PAPER research.

Run from Windows Task Scheduler. Records explicit DEFERRED_LOW_MEMORY instead of
forcing MLflow/scikit imports during paging pressure. Never touches active
Council weights, Paper monitor state, or a broker.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def available_memory_mb() -> int:
    if os.name == "nt":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong), ("memory_load", ctypes.c_ulong),
                ("total_phys", ctypes.c_ulonglong), ("available_phys", ctypes.c_ulonglong),
                ("total_pagefile", ctypes.c_ulonglong), ("available_pagefile", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong), ("available_virtual", ctypes.c_ulonglong),
                ("available_extended_virtual", ctypes.c_ulonglong),
            ]
        data = MemoryStatus()
        data.length = ctypes.sizeof(data)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(data)):
            raise OSError("Cannot determine available Windows memory")
        return int(data.available_phys // (1024 * 1024))
    meminfo = Path("/proc/meminfo").read_text(encoding="utf-8")
    for line in meminfo.splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) // 1024
    raise OSError("Cannot determine available RAM")


def publish_status(path: Path, status: str, **details: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status, "training_environment": "PAPER_RESEARCH_ONLY",
        "broker_execution_allowed": False, "active_council_weights_changed": False,
        **details,
    }
    fd, name = tempfile.mkstemp(prefix=".atlas-research-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, allow_nan=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def run_research(*, root: Path, journal: Path, min_available_mb: int = 1200) -> int:
    status = root / "evidence" / "scheduler-status.json"
    report = root / "evidence" / "council-agent-scores.json"
    src = root / "training-src"
    if not journal.is_file() or not (src / "atlas_training" / "council_sklearn_research.py").is_file():
        publish_status(status, "FAILED_MISSING_INPUTS")
        return 2
    try:
        memory_mb = available_memory_mb()
    except OSError as exc:
        publish_status(status, "FAILED_MEMORY_CHECK", reason=str(exc))
        return 2
    if memory_mb < min_available_mb:
        publish_status(status, "DEFERRED_LOW_MEMORY", available_mb=memory_mb,
                       required_mb=min_available_mb)
        return 3
    file_hash = hashlib.sha256(journal.read_bytes()).hexdigest()
    if status.is_file():
        try:
            previous = json.loads(status.read_text(encoding="utf-8"))
            if (previous.get("status") == "SUCCESS"
                    and previous.get("source_sha256") == file_hash
                    and previous.get("generated_at", "")[:10] == datetime.now(timezone.utc).date().isoformat()):
                publish_status(status, "SKIPPED_ALREADY_EVALUATED", source_sha256=file_hash)
                return 0
        except (OSError, ValueError):
            pass

    db = root / "mlflow.db"
    if not db.is_file():
        publish_status(status, "FAILED_MLFLOW_DB_MISSING")
        return 2
    sqlite_uri = "sqlite:///" + db.as_posix()
    args = [sys.executable, "-m", "atlas_training.council_sklearn_research",
            "--journal", str(journal), "--report", str(report),
            "--mlflow-uri", sqlite_uri]
    env = os.environ.copy()
    env.update({"ATLAS_LIVE_TRADING": "false",
                "ATLAS_REAL_MONEY_EXECUTION": "false",
                "ATLAS_DEMO_ORDER_EXECUTION": "false",
                "ATLAS_DASHBOARD_ONLY": "true",
                "OPENBLAS_NUM_THREADS": "1",
                "OMP_NUM_THREADS": "1",
                "MKL_NUM_THREADS": "1",
                "PYTHONDONTWRITEBYTECODE": "1"})
    publish_status(status, "RUNNING", available_mb=memory_mb, source_sha256=file_hash)
    try:
        result = subprocess.run(args, cwd=src, env=env, capture_output=True,
                                text=True, timeout=600, check=False)
    except subprocess.TimeoutExpired:
        publish_status(status, "FAILED_TIMEOUT", source_sha256=file_hash)
        return 4
    except OSError as exc:
        publish_status(status, "FAILED_PROCESS", reason=str(exc), source_sha256=file_hash)
        return 2
    (root / "evidence" / "last-evaluation-stdout.log").write_text(result.stdout[-20000:], encoding="utf-8")
    (root / "evidence" / "last-evaluation-stderr.log").write_text(result.stderr[-20000:], encoding="utf-8")
    if result.returncode or not report.is_file():
        publish_status(status, "FAILED_EVALUATION", subprocess_exit=result.returncode, source_sha256=file_hash)
        return 2
    try:
        evidence = json.loads(report.read_text(encoding="utf-8"))
        if (evidence.get("source_sha256") != file_hash
                or evidence.get("active_council_weights_changed") is not False
                or evidence.get("broker_execution_allowed") is not False
                or not evidence.get("mlflow_run_id")):
            raise ValueError("Missing/contradictory training evidence")
    except (OSError, ValueError) as exc:
        publish_status(status, "FAILED_UNVERIFIED_EVIDENCE", reason=str(exc), source_sha256=file_hash)
        return 2
    publish_status(status, "SUCCESS", source_sha256=file_hash,
                   mlflow_run_id=evidence["mlflow_run_id"], review_status=evidence["status"])
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Resource-safe read-only PAPER research scheduler.")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--journal", required=True, type=Path)
    args = parser.parse_args()
    result = run_research(root=args.root, journal=args.journal)
    print(json.dumps({"scheduler_status_exit": result, "active_council_weights_changed": False}))
    return result


if __name__ == "__main__":
    raise SystemExit(main())
