import numpy as np
import pytest
pd = pytest.importorskip("pandas")
pytest.importorskip("sklearn")
from atlas_training.train_agent import (
    evaluate_promotion_gate,
    load_prices,
    make_features,
    walk_forward_metrics,
    walk_forward_score,
)


def prices(n=170):
    rng = np.random.default_rng(7)
    close = 2000 * np.exp(np.cumsum(rng.normal(0, .002, n)))
    return pd.DataFrame({
        "time": pd.date_range("2026-01-01", periods=n, freq="15min", tz="UTC"),
        "open": close,
        "high": close + 2,
        "low": close - 2,
        "close": close,
    })


def test_no_unknown_last_label():
    X, y = make_features(prices())
    assert len(X) == 170 - 10
    assert len(y) == len(X)
    assert X.notna().all().all()


def test_cv_finite():
    X, y = make_features(prices())
    mean, std, scores = walk_forward_score(X, y, folds=5)
    assert len(scores) == 5 and 0 <= mean <= 1 and std >= 0
    m = walk_forward_metrics(X, y, folds=5)
    assert 0 <= m["train_mean"] <= 1
    assert m["stability"] >= 0
    assert 0 <= m["calibration_error"] <= 1


def test_reject_duplicate_times(tmp_path):
    df = prices()
    df.loc[2, "time"] = df.loc[1, "time"]
    path = tmp_path / "prices.csv"
    df.to_csv(path, index=False)
    with pytest.raises(ValueError, match="Duplicate"):
        load_prices(str(path))


def test_reject_bad_ohlc(tmp_path):
    df = prices()
    df.loc[4, "high"] = df.loc[4, "close"] - 10
    path = tmp_path / "prices.csv"
    df.to_csv(path, index=False)
    with pytest.raises(ValueError, match="OHLC"):
        load_prices(str(path))


def test_promotion_gate_blocks_weak_first_model():
    weak_metrics = {
        "oos_mean": 0.2894,
        "train_mean": 0.6500,
        "stability": 0.2894 / 0.6500,
        "calibration_error": 0.2500,
    }
    ok, reasons = evaluate_promotion_gate(weak_metrics, previous_champion_score=None)
    assert not ok
    assert any("below baseline floor" in r for r in reasons)
    assert any("Stability" in r for r in reasons)
    assert any("Calibration error" in r for r in reasons)


def test_promotion_gate_passes_valid_challenger():
    strong_metrics = {
        "oos_mean": 0.5600,
        "train_mean": 0.6200,
        "stability": 0.5600 / 0.6200,
        "calibration_error": 0.0600,
    }
    ok, reasons = evaluate_promotion_gate(strong_metrics, previous_champion_score=0.5400)
    assert ok
    assert reasons == []
