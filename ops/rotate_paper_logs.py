"""Stream a paper worker directly into bounded logs, preserving its exit code."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import os
from pathlib import Path
import subprocess
import sys


@contextmanager
def writer_lock(path):
    with path.with_name(path.name + ".writer.lock").open("a+b") as lock:
        lock.seek(0, 2)
        if lock.tell() == 0:
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def stream(path, source, limit=16 * 1024 * 1024, keep=3):
    def roll():
        for i in range(keep, 0, -1):
            previous = path.with_name(path.name + "." + str(i))
            if previous.exists():
                if i == keep:
                    previous.unlink()
                else:
                    os.replace(previous, path.with_name(path.name + "." + str(i + 1)))
        if path.exists():
            os.replace(path, path.with_name(path.name + ".1"))
    if path.exists() and path.stat().st_size >= limit:
        roll()
    out = path.open("ab", buffering=0)
    try:
        for line in iter(lambda: source.read1(65536), b""):
            if out.tell() and out.tell() + len(line) > limit:
                out.close()
                roll()
                out = path.open("ab", buffering=0)
            out.write(line)
    finally:
        out.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument("--run", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    args.log.parent.mkdir(parents=True, exist_ok=True)
    with writer_lock(args.log):
        if args.run is None:
            stream(args.log, sys.stdin.buffer)
            return 0
        if not args.run:
            parser.error("--run needs a worker command")
        # No PowerShell native-command pipeline: stderr is diagnostic data, not a terminating error.
        child = subprocess.Popen(args.run, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        try:
            with child.stdout:
                stream(args.log, child.stdout)
            return child.wait()
        finally:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()


if __name__ == "__main__":
    raise SystemExit(main())
