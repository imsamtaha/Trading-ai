"""One OS-owned writer lock shared by offline and API training sessions."""
from contextlib import contextmanager
import errno
import os
from pathlib import Path


class TrainingBusy(RuntimeError):
    pass


@contextmanager
def training_lock(prefix):
    path = Path(str(Path(prefix).resolve()) + ".training.lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Never unlink this inode: waiters must lock the same persistent file.
    handle = path.open("a+b")
    locked = False
    try:
        if os.name == "nt":
            import msvcrt
            if path.stat().st_size == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise TrainingBusy("TRAINING_BUSY") from exc
        else:
            import fcntl
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                if exc.errno in (errno.EACCES, errno.EAGAIN):
                    raise TrainingBusy("TRAINING_BUSY") from exc
                raise
        locked = True
        yield
    finally:
        if locked:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()
