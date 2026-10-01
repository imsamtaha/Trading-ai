"""Windows supervisor: recover stopped web tasks; observe MT5 without orders."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

class FailureGate:
    def __init__(self, state=None):
        self.state = dict(state or {"failures": 0, "attempts": 0, "next": 0})
    def observe(self, healthy, now):
        if healthy:
            self.state.update(failures=0, attempts=0, next=0)
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
        capture_output=True, text=True, timeout=10, creationflags=0x08000000)
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
    for name, task, url in (
        ("backend", "ATLAS Private Backend", "http://127.0.0.1:8012/health"),
        ("frontend", "ATLAS Web Frontend", "http://127.0.0.1:8011/connect"),
    ):
        healthy = http_health(url)
        gate = FailureGate(saved.get(name))
        due = gate.observe(healthy, now)
        component = {"state": "HEALTHY" if healthy else "HTTP_UNAVAILABLE"}
        if due:
            try:
                task_state = powershell("(Get-ScheduledTask -TaskName '" + task + "').State.ToString()")
                component["task_state"] = task_state
                if task_state == "Ready":
                    powershell("Start-ScheduledTask -TaskName '" + task + "'")
                    status["actions"].append("STARTED " + task)
                elif task_state == "Running":
                    component["state"] = "RUNNING_BUT_UNHEALTHY"
                else:
                    component["state"] = "TASK_REQUIRES_ATTENTION"
            except Exception:
                component["state"] = "TASK_OPERATION_FAILED"
        saved[name] = gate.state
        status["components"][name] = component
    status["components"]["public_route"] = {"state":
        "HTTPS_REACHABLE" if http_health("https://justai-atlas.online/connect") else "HTTPS_UNAVAILABLE"}
    status["components"]["mt5"] = check_mt5()
    atomic_json(state_path, saved)
    atomic_json(directory / "status.json", status)
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
    directory = Path(args.state_dir or Path.home() / "ATLAS_Backup" / "server")
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

