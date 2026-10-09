"""Validate an isolated frontend build, promote it, and roll back failed health checks."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import urllib.request
from urllib.parse import urlsplit
import uuid

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "runtime" / "web-ui"
STATE = ROOT / ".runtime" / "server"

def task(action):
    code = "$ErrorActionPreference='Stop'; " + action + "-ScheduledTask -TaskName 'ATLAS Web Frontend'"
    if action == "Stop":
        code += "; $deadline=(Get-Date).AddSeconds(15); while ((Get-ScheduledTask -TaskName 'ATLAS Web Frontend').State -eq 'Running') { if ((Get-Date) -ge $deadline) { throw 'Stop timeout' }; Start-Sleep -Milliseconds 200 }"
    subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", code], check=True, timeout=25)

def health(base, assets=False):
    try:
        for route in ("/login", "/dashboard", "/backend/health", "/backend/auth/config"):
            with urllib.request.urlopen(base + route, timeout=6) as r:
                if r.status != 200: return False
                body=r.read().decode("utf-8")
            if route == "/backend/health":
                payload = json.loads(body)
                if not isinstance(payload, dict) or payload.get("status") != "healthy" or payload.get("service") != "atlas-trading-api":
                    return False
            if route == "/backend/auth/config":
                payload = json.loads(body)
                if not isinstance(payload, dict): return False
                auth_url = payload.get("url")
                key = payload.get("anon_key")
                if not isinstance(auth_url, str) or not isinstance(key, str) or not key.strip(): return False
                target = urlsplit(auth_url)
                if target.scheme != "https" or not target.hostname: return False
            if assets and route == "/login":
                scripts = [src for src in re.findall(r'<script[^>]+src="([^"]+)"', body) if src.startswith("/_next/")]
                if not scripts: return False
                for src in scripts:
                    with urllib.request.urlopen(base + src, timeout=6) as r:
                        if r.status != 200: return False
        return True
    except Exception:
        return False

def wait_health():
    deadline=time.monotonic()+45
    while time.monotonic() < deadline:
        if health("http://127.0.0.1:8011", assets=True): return True
        time.sleep(2)
    return False

def promote(web, candidate, state):
    web=web.resolve(); candidate=candidate.resolve()
    if candidate.parent != web or not candidate.name.startswith(".next-candidate") or not (candidate / "BUILD_ID").is_file():
        raise ValueError("INVALID_CANDIDATE")
    live=web / ".next-production"; backup=web / ".next-last-good"
    if not (live / "BUILD_ID").is_file(): raise ValueError("LAST_GOOD_PRODUCTION_REQUIRED")
    state.mkdir(parents=True, exist_ok=True)
    marker=state / "maintenance.json"
    marker.write_text(json.dumps({"expires_at":time.time()+900}), encoding="utf-8")
    moved=False
    try:
        task("Stop")
        if backup.exists(): shutil.rmtree(backup)
        live.rename(backup); moved=True
        candidate.rename(live)
        task("Start")
        if not wait_health(): raise RuntimeError("POST_DEPLOY_HEALTH_FAILED")
    except Exception as exc:
        if moved:
            try:
                task("Stop")
                if live.exists(): shutil.rmtree(live)
                backup.rename(live)
                task("Start")
                recovered=wait_health()
            except Exception as rollback_error:
                raise RuntimeError("ROLLBACK_REQUIRES_ATTENTION") from rollback_error
            if not recovered: raise RuntimeError("ROLLBACK_HEALTH_FAILED") from exc
            raise RuntimeError("DEPLOYMENT_FAILED_ROLLED_BACK") from exc
        task("Start")
        raise
    finally:
        marker.unlink(missing_ok=True)

def validate_frontend(node, web, env):
    # Lint is an admission check, rather than a manual step that upgrades skip.
    for args in (["node_modules/vitest/vitest.mjs", "run"],
                 ["node_modules/eslint/bin/eslint.js", ".", "--max-warnings=0"],
                 ["node_modules/typescript/bin/tsc", "--noEmit"],
                 ["node_modules/next/dist/bin/next", "build"]):
        subprocess.run([node, *args], cwd=web, env=env, check=True)

def main():
    import msvcrt
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / "deployment.lock").open("a+b") as lock:
        if lock.tell()==0: lock.write(b"0"); lock.flush()
        lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        node=shutil.which("node.exe")
        if not node: raise RuntimeError("NODE_UNAVAILABLE")
        candidate=WEB / (".next-candidate-" + uuid.uuid4().hex[:8])
        env=dict(os.environ, ATLAS_BUILD_DIR=candidate.name, ATLAS_BACKEND_ORIGIN="http://127.0.0.1:8012")
        original={p:p.read_bytes() for p in (WEB / "next-env.d.ts", WEB / "tsconfig.json")}
        canary=None
        try:
            validate_frontend(node, WEB, env)
            # No promotion without a running, verified isolated build. The port
            # must be unused; a stale canary is never accepted as this build.
            import socket
            with socket.socket() as probe: probe.bind(("127.0.0.1",8014))
            canary=subprocess.Popen([node,"node_modules/next/dist/bin/next","start","--hostname","127.0.0.1","--port","8014"],cwd=WEB,env=env)
            deadline=time.monotonic()+45; ready=False
            while canary.poll() is None and time.monotonic()<deadline:
                if health("http://127.0.0.1:8014",assets=True): ready=True; break
                time.sleep(2)
            if not ready: raise RuntimeError("CANARY_HEALTH_FAILED_PRODUCTION_UNCHANGED")
            subprocess.run(["taskkill.exe","/PID",str(canary.pid),"/T","/F"],check=True,stdout=subprocess.DEVNULL)
            canary.wait(timeout=10); canary=None
            promote(WEB,candidate,STATE)
            print("DEPLOYED_AND_VERIFIED")
        finally:
            if canary is not None and canary.poll() is None:
                subprocess.run(["taskkill.exe","/PID",str(canary.pid),"/T","/F"],stdout=subprocess.DEVNULL)
            for path,data in original.items(): path.write_bytes(data)
            if candidate.exists(): shutil.rmtree(candidate)

if __name__ == "__main__": main()
