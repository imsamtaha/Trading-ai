"""Serialize automatic MT5 checks and submission across local worker processes."""
from contextlib import contextmanager
from pathlib import Path
from tempfile import gettempdir
from threading import Lock
import os


class ExecutionBusy(RuntimeError):
    pass


_THREAD_LOCK = Lock()
# Same user/host MT5 sessions share this path across checkouts and symbols.
_LOCK_PATH = Path(gettempdir()) / 'atlas-mt5-portfolio.lock'


@contextmanager
def portfolio_lock():
    if not _THREAD_LOCK.acquire(blocking=False):
        raise ExecutionBusy('Another automatic execution is in progress.')
    handle = None
    acquired = False
    try:
        handle = _LOCK_PATH.open('a+b')
        if handle.seek(0, 2) == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except OSError as exc:
            raise ExecutionBusy('Automatic execution lock unavailable.') from exc
        yield
    finally:
        if handle is not None:
            try:
                if acquired:
                    handle.seek(0)
                    if os.name == 'nt':
                        import msvcrt
                        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            finally:
                handle.close()
        _THREAD_LOCK.release()
