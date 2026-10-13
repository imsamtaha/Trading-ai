import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_runner_streams_stdout_stderr_and_preserves_child_exit(tmp_path):
    log = tmp_path / "paper.log"
    code = "import sys; print('paper-started',flush=True); print('diagnostic',file=sys.stderr); sys.exit(7)"
    result = subprocess.run([sys.executable, str(ROOT/"ops/rotate_paper_logs.py"),
                             str(log), "--run", sys.executable, "-u", "-c", code],
                            input=b"", capture_output=True, timeout=15)
    assert result.returncode == 7, result.stderr
    assert b"paper-started" in log.read_bytes()
    assert b"diagnostic" in log.read_bytes()

def test_existing_oversized_log_rotated_before_child_starts(tmp_path):
    log = tmp_path / "paper.log"
    log.write_bytes(b"x" * (16 * 1024 * 1024 + 1))
    result = subprocess.run([sys.executable, str(ROOT/"ops/rotate_paper_logs.py"),
                             str(log), "--run", sys.executable, "-u", "-c",
                             "print('fresh-cycle',flush=True)"],
                            input=b"", capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert log.with_name("paper.log.1").stat().st_size > 16 * 1024 * 1024
    assert b"fresh-cycle" in log.read_bytes()

def test_output_reaches_log_before_worker_exits_and_duplicate_refused(tmp_path):
    import time
    log=tmp_path/"paper.log"
    command=[sys.executable,str(ROOT/"ops/rotate_paper_logs.py"),str(log),
             "--run",sys.executable,"-u","-c",
             "import sys; print('running',flush=True); sys.stdin.readline()"]
    worker=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        deadline=time.monotonic()+5
        while time.monotonic()<deadline and (not log.exists() or b"running" not in log.read_bytes()):
            time.sleep(.05)
        assert log.exists() and b"running" in log.read_bytes()
        assert worker.poll() is None
        duplicate=subprocess.run(command,input=b"done\n",capture_output=True,timeout=10)
        assert duplicate.returncode!=0
        stdout,stderr=worker.communicate(b"done\n",timeout=10)
        assert worker.returncode==0,stderr
    finally:
        if worker.poll() is None:
            worker.communicate(b"done\n",timeout=10)

def test_single_oversized_line_respects_active_log_limit(tmp_path):
    log=tmp_path/"paper.log"
    code="import sys; sys.stdout.buffer.write(b'x'*(17*1024*1024)); sys.stdout.flush()"
    result=subprocess.run([sys.executable,str(ROOT/"ops/rotate_paper_logs.py"),str(log),
                           "--run",sys.executable,"-u","-c",code],
                          input=b"",capture_output=True,timeout=15)
    assert result.returncode==0,result.stderr
    assert log.stat().st_size<=16*1024*1024
