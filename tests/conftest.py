import pytest

from app.execution import portfolio_lock


@pytest.fixture(autouse=True, scope="session")
def isolate_mt5_portfolio_lock(tmp_path_factory):
    # Keep the real OS lock behavior without using a running worker's lock.
    lock_path = tmp_path_factory.mktemp("mt5-lock") / "portfolio.lock"
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(portfolio_lock, "_LOCK_PATH", lock_path)
        yield
