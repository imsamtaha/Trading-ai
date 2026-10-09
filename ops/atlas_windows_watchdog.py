"""Windows supervisor: recover stopped web tasks; observe MT5 without orders."""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

class FailureGate:
    def __init__(self, state=None):
        self.state = dict(state or {"failures": 0, "attempts": 0, "next": 0})
        self.state.setdefault("recoveries", self.state.get("restarts", 0))
    def observe(self, healthy, now):
        if healthy:
            self.state.update(failures=0, attempts=0, restarts=0, recoveries=0, next=0)
            return False
        self.state["failures"] = self.state.get("failures", 0) + 1
        if self.state["failures"] < 3 or now < self.state.get("next", 0):
            return False
        attempt = self.state.get("attempts", 0)
        delay = (30, 60, 120)[attempt] if attempt < 3 else 300
        self.state.update(attempts=attempt + 1, next=now + delay)
        return True

def atomic_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    os.replace(temporary, path)

def powershell(code):
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive",
        "-Command", "$ErrorActionPreference='Stop'; " + code],
        capture_output=True, text=True, timeout=30, creationflags=0x08000000)
    if result.returncode:
        raise RuntimeError("WINDOWS_TASK_OPERATION_FAILED")
    return result.stdout.strip()

def http_health(url):
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "ATLAS-Windows-Monitor/1.0"})
        with urllib.request.urlopen(request, timeout=6) as response:
            return response.status == 200
    except Exception:
        return False

def mt5_probe():
    import MetaTrader5 as mt5
    try:
        if not mt5.initialize(r"C:\Program Files\MetaTrader 5\terminal64.exe", timeout=8000):
            return {"state": "MT5_UNAVAILABLE"}
        account, terminal = mt5.account_info(), mt5.terminal_info()
        if account is None or terminal is None:
            return {"state": "AUTH_REQUIRED"}
        if (account.login != 592031391 or account.server != "FxPro-MT5 Demo"
                or account.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO):
            return {"state": "ACCOUNT_MISMATCH"}
        positions = mt5.positions_get()
        state = ("MT5_OFFLINE" if not terminal.connected else
                 "ALGO_DISABLED" if not terminal.trade_allowed or terminal.tradeapi_disabled else
                 "POSITION_DATA_UNAVAILABLE" if positions is None else "HEALTHY")
        return {"state": state, "open_positions": None if positions is None else len(positions)}
    finally:
        mt5.shutdown()

def check_mt5():
    try:
        result = subprocess.run([sys.executable, __file__, "--mt5-probe"],
            capture_output=True, text=True, timeout=12, creationflags=0x08000000)
        return json.loads(result.stdout) if result.returncode == 0 else {"state": "PROBE_FAILED"}
    except Exception:
        return {"state": "PROBE_TIMEOUT_OR_FAILED"}

def check_cycle(directory):
    state_path = directory / "recovery-state.json"
    try:
        saved = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = {}
    now = time.time()
    status = {"checked_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "components": {}, "actions": []}
    try:
        maintenance = json.loads((directory / "maintenance.json").read_text())
        paused = 0 < float(maintenance.get("expires_at", 0)) - now <= 900
    except (OSError, ValueError, TypeError):
        paused = False
    status["maintenance"] = paused
    for name, task, url in (
        ("backend", "ATLAS Private Backend", "http://127.0.0.1:8012/health"),
        ("frontend", "ATLAS Web Frontend", "http://127.0.0.1:8011/connect"),
        ("tunnel", "ATLAS Tunnel Recovery", "https://justai-atlas.online/connect"),
    ):
        healthy = http_health(url)
        gate = FailureGate(saved.get(name))
        local_healthy = all(status["components"].get(k, {}).get("state") == "HEALTHY" for k in ("backend", "frontend"))
        eligible = name != "tunnel" or local_healthy
        due = gate.observe(healthy, now) if eligible and not paused else False
        component = {"state": "HEALTHY" if healthy else "HTTP_UNAVAILABLE"}
        if not healthy and gate.state["recoveries"] >= 5:
            component["state"] = "RECOVERY_EXHAUSTED"
        if due:
            try:
                task_state = powershell("(Get-ScheduledTask -TaskName '" + task + "').State.ToString()")
                component["task_state"] = task_state
                if task_state in {"Ready", "Running"}:
                    if gate.state["recoveries"] >= 5:
                        component["state"] = "RECOVERY_EXHAUSTED"
                    else:
                        # Failed requests consume the same bounded budget as
                        # successful ones; stopped tasks cannot loop forever.
                        gate.state["recoveries"] += 1
                        # Only the named web and tunnel tasks are eligible. Never restart
                        # an execution worker or touch MT5 account permissions.
                        if task_state == "Ready":
                            powershell("Start-ScheduledTask -TaskName '" + task + "'")
                            component["state"] = "START_REQUESTED"
                            status["actions"].append("STARTED " + task)
                        else:
                            gate.state["restarts"] = gate.state.get("restarts", 0) + 1
                            powershell("Stop-ScheduledTask -TaskName '" + task + "'; "
                                "$deadline = (Get-Date).AddSeconds(10); "
                                "while ((Get-ScheduledTask -TaskName '" + task + "').State.ToString() -eq 'Running') { "
                                "if ((Get-Date) -ge $deadline) { throw 'Task stop timed out' }; "
                                "Start-Sleep -Milliseconds 200 }; "
                                "Start-ScheduledTask -TaskName '" + task + "'")
                            component["state"] = "RECOVERING"
                            status["actions"].append("RESTARTED " + task)
                else:
                    component["state"] = "TASK_REQUIRES_ATTENTION"
            except Exception:
                component["state"] = "TASK_OPERATION_FAILED"
        saved[name] = gate.state
        status["components"][name] = component
    status["components"]["public_route"] = {"state":
        "HTTPS_REACHABLE" if status["components"]["tunnel"]["state"] == "HEALTHY" else "HTTPS_UNAVAILABLE"}
    # The paper task cannot place broker orders. Start only a stopped task;
    # a running task without a completed cycle is reported, never duplicated.
    paper_gate = FailureGate(saved.get("paper"))
    paper = {"state": "TASK_OPERATION_FAILED"}
    try:
        task_state = powershell("(Get-ScheduledTask -TaskName 'ATLAS Paper Monitor').State.ToString()")
        paper["task_state"] = task_state
        if task_state == "Running":
            try:
                heartbeat = json.loads((directory.parent / "paper" / "paper-cycle.json").read_text(encoding="utf-8"))
                modified = heartbeat.get("checked_at_epoch") if isinstance(heartbeat, dict) else None
                if isinstance(modified, bool) or not isinstance(modified, (int, float)) or not math.isfinite(modified):
                    raise ValueError("INVALID_PAPER_HEARTBEAT")
                age = now - modified
                fresh = (0 <= age <= 120 and modified >= paper_gate.state.get("started_at", 0)
                         and heartbeat.get("state") == "COMPLETED"
                         and heartbeat.get("broker_execution_allowed") is False)
                paper["cycle_age_seconds"] = round(age, 1)
            except (OSError, ValueError, TypeError):
                fresh = False
            paper["state"] = "HEALTHY" if fresh else "HEARTBEAT_UNAVAILABLE"
            if fresh:
                paper_gate.observe(True, now)
                paper_gate.state["starts"] = 0
        elif task_state == "Ready":
            paper["state"] = "STOPPED"
            if paper_gate.state.get("starts", 0) >= 5:
                paper["state"] = "RECOVERY_EXHAUSTED"
            elif not paused and paper_gate.observe(False, now):
                paper_gate.state["starts"] = paper_gate.state.get("starts", 0) + 1
                paper_gate.state["started_at"] = now
                powershell("Start-ScheduledTask -TaskName 'ATLAS Paper Monitor'")
                paper["state"] = "START_REQUESTED"
                status["actions"].append("STARTED ATLAS Paper Monitor")
        else:
            paper["state"] = "TASK_REQUIRES_ATTENTION"
    except Exception:
        paper["state"] = "TASK_OPERATION_FAILED"
    saved["paper"] = paper_gate.state
    status["components"]["paper"] = paper
    status["components"]["mt5"] = check_mt5()
    atomic_json(state_path, saved)
    atomic_json(directory / "status.json", status)
    healthy_states = {"HEALTHY", "HTTPS_REACHABLE", "ALGO_DISABLED"}
    atomic_json(directory / "attention.json", {
        "checked_at_utc": status["checked_at_utc"],
        "maintenance": paused,
        "components": {name: item["state"] for name, item in status["components"].items()
                       if item["state"] not in healthy_states},
    })
    log = directory / "events.jsonl"
    if log.exists() and log.stat().st_size > 1_000_000:
        os.replace(log, directory / "events.previous.jsonl")
    with log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(status) + "\n")
    return status

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mt5-probe", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--state-dir", required=False)
    args = parser.parse_args()
    if args.mt5_probe:
        print(json.dumps(mt5_probe()))
        return
    directory = Path(args.state_dir or Path.home() / "ATLAS" / ".runtime" / "server")
    directory.mkdir(parents=True, exist_ok=True)
    import msvcrt
    with (directory / "supervisor.lock").open("a+b") as lock:
        if lock.tell() == 0:
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise SystemExit("Supervisor already running")
        while True:
            started = time.monotonic()
            try:
                status = check_cycle(directory)
                if args.once:
                    print(json.dumps(status))
                    return
            except Exception as exc:
                atomic_json(directory / "supervisor-error.json",
                    {"type": type(exc).__name__, "time": time.time()})
                if args.once:
                    raise
            time.sleep(max(1, 30 - (time.monotonic() - started)))

if __name__ == "__main__":
    main()
