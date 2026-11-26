"""Build and promote a frontend while retaining every previous production bundle."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid
import msvcrt
from deploy_atlas_web import health, task, wait_health

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/"runtime/web-ui"
STATE=ROOT/".runtime/server"

def main():
    STATE.mkdir(parents=True,exist_ok=True)
    with (STATE/"deployment.lock").open("a+b") as lock:
        if lock.tell()==0: lock.write(b"0");lock.flush()
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        token=time.strftime("%Y%m%d-%H%M%S")+"-"+uuid.uuid4().hex[:6]
        candidate=WEB/(".next-candidate-"+token)
        previous=WEB/(".next-retained-"+token)
        failed=WEB/(".next-failed-"+token)
        live=WEB/".next-production"
        if not (live/"BUILD_ID").is_file():raise RuntimeError("LAST_GOOD_REQUIRED")
        assert not any(p.exists() for p in (candidate,previous,failed))
        node=shutil.which("node.exe")
        if not node: raise RuntimeError("NODE_REQUIRED")
        env=dict(os.environ,ATLAS_BUILD_DIR=candidate.name,ATLAS_BACKEND_ORIGIN="http://127.0.0.1:8012")
        originals={p:p.read_bytes() for p in (WEB/"next-env.d.ts",WEB/"tsconfig.json")}
        canary=None;moved=False;promoted=False
        marker=STATE/"maintenance.json"
        try:
            subprocess.run([node,"node_modules/typescript/bin/tsc","--noEmit"],cwd=WEB,env=env,check=True)
            subprocess.run([node,"node_modules/next/dist/bin/next","build"],cwd=WEB,env=env,check=True)
            if not (candidate/"BUILD_ID").is_file():raise RuntimeError("BUILD_ID_MISSING")
            import socket
            with socket.socket() as probe:probe.bind(("127.0.0.1",8014))
            canary=subprocess.Popen([node,"node_modules/next/dist/bin/next","start","--hostname","127.0.0.1","--port","8014"],cwd=WEB,env=env)
            print("OWNED_CANARY",canary.pid,"node next start port 8014",flush=True)
            deadline=time.monotonic()+45
            while canary.poll() is None and time.monotonic()<deadline:
                if health("http://127.0.0.1:8014",assets=True):break
                time.sleep(2)
            else:raise RuntimeError("CANARY_FAILED_PRODUCTION_UNCHANGED")
            print("CANARY_HEALTH_VERIFIED",flush=True)
            # Only terminate the exact subprocess tree created by this script.
            subprocess.run(["taskkill.exe","/PID",str(canary.pid),"/T","/F"],check=True)
            canary.wait(timeout=10);canary=None
            marker.write_text(json.dumps({"expires_at":time.time()+900}),encoding="utf-8")
            task("Stop")
            live.rename(previous);moved=True
            candidate.rename(live);promoted=True
            task("Start")
            if not wait_health():raise RuntimeError("PRODUCTION_HEALTH_FAILED")
            print("DEPLOYED_AND_VERIFIED",live.name,"PREVIOUS_RETAINED",previous.name,flush=True)
        except Exception:
            if moved:
                task("Stop")
                if promoted:live.rename(failed)
                previous.rename(live)
                task("Start")
                if not wait_health():raise RuntimeError("ROLLBACK_HEALTH_FAILED")
                print("ROLLED_BACK_PREVIOUS_PRODUCTION",flush=True)
            raise
        finally:
            if canary is not None and canary.poll() is None:
                print("STOPPING_OWNED_CANARY",canary.pid,flush=True)
                subprocess.run(["taskkill.exe","/PID",str(canary.pid),"/T","/F"],check=True)
            for path,data in originals.items():path.write_bytes(data)
            if marker.exists():marker.unlink()
            # Candidate, failed, and retained bundles are kept for review/recovery.
if __name__=="__main__":main()
