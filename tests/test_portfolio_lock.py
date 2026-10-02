import multiprocessing
from pathlib import Path

import pytest
from app.execution import portfolio_lock as module


def hold_lock(path, entered, release):
    from app.execution import portfolio_lock as lock_module
    lock_module._LOCK_PATH = Path(path)
    with lock_module.portfolio_lock():
        entered.set()
        if not release.wait(10):
            raise RuntimeError('Test release timeout')


def test_lock_serializes_separate_worker_processes_and_releases(tmp_path, monkeypatch):
    path = tmp_path / 'portfolio.lock'
    monkeypatch.setattr(module, '_LOCK_PATH', path)
    ctx = multiprocessing.get_context('spawn')
    entered, release = ctx.Event(), ctx.Event()
    process = ctx.Process(target=hold_lock, args=(str(path), entered, release))
    process.start()
    try:
        assert entered.wait(5)
        with pytest.raises(module.ExecutionBusy):
            with module.portfolio_lock():
                pytest.fail('Second worker was allowed into portfolio checks')
    finally:
        release.set()
        process.join(5)
        if process.is_alive():
            process.terminate()
            process.join()
    assert process.exitcode == 0
    with module.portfolio_lock():
        pass


def test_lock_releases_after_risk_or_submission_exception(tmp_path, monkeypatch):
    monkeypatch.setattr(module, '_LOCK_PATH', tmp_path / 'portfolio.lock')
    with pytest.raises(ValueError):
        with module.portfolio_lock():
            raise ValueError('Risk failed')
    with module.portfolio_lock():
        pass
