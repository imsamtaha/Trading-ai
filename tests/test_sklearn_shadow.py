"""Offline/SHADOW scikit-learn smoke and safety regression tests."""
import hashlib
import json
import sys

import numpy as np
import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("sklearn")

from atlas_training.sklearn_shadow import (
    backend_check,
    evaluate_csv,
    main,
    write_shadow_report,
)


def _csv(tmp_path, n=170):
    rng = np.random.default_rng(7)
    close = 2000 * np.exp(np.cumsum(rng.normal(0, 0.002, n)))
    prices = pd.DataFrame({
        "time": pd.date_range("2026-01-01", periods=n, freq="15min", tz="UTC"),
        "open": close, "high": close + 2, "low": close - 2, "close": close,
    })
    path = tmp_path / "synthetic_OHLC_not_real_broker.csv"
    prices.to_csv(path, index=False)
    return path


def test_android_style_native_fit_predict_does_not_change_runtime():
    report = backend_check()
    assert report["status"] == "READY_FOR_OFFLINE_RESEARCH"
    assert report["broker_execution_allowed"] is False
    assert report["council_weight_activation"] is False
    assert report["model_registered"] is False


def test_shadow_csv_reuses_walk_forward_and_records_provenance(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "mlflow", None)
    monkeypatch.setitem(sys.modules, "MetaTrader5", None)
    source = _csv(tmp_path)
    source_bytes = source.read_bytes()
    result = evaluate_csv(source, agent="STC-04")
    assert result["source_sha256"] == hashlib.sha256(source_bytes).hexdigest()
    assert result["source_rows"] == 170
    assert result["evaluation_rows"] == 160
    assert len(result["metrics"]["oos_scores"]) == 5
    assert result["status"] in ("REJECTED", "SHADOW_REVIEW")
    assert result["training_environment"] == "OFFLINE_RESEARCH"
    assert result["broker_execution_allowed"] is False
    assert result["council_weight_activation"] is False
    assert result["model_registered"] is False
    assert result["champion_promoted"] is False
    assert source.read_bytes() == source_bytes


def test_shadow_report_is_explicit_and_atomic(tmp_path):
    source = _csv(tmp_path)
    result = evaluate_csv(source, agent="STC-09")
    path = tmp_path / "research" / "shadow.json"
    write_shadow_report(path, result)
    saved = json.loads(path.read_text())
    assert saved == result
    assert saved["feature_scope"] == "ILLUSTRATIVE_NOT_LIVE_SIGNALS"
    assert saved["reviewers"] == ["STC-04", "STC-09"]
    assert list(tmp_path.glob("**/.sklearn-shadow-*")) == []


def test_invalid_report_preserves_previous_evidence(tmp_path):
    target = tmp_path / "report.json"
    target.write_text('{"previous":"approved-by-human"}\n')
    with pytest.raises(ValueError):
        write_shadow_report(target, {"metrics": float("nan")})
    assert json.loads(target.read_text())["previous"] == "approved-by-human"
    assert list(tmp_path.glob(".sklearn-shadow-*")) == []


def test_bad_csv_fails_closed_and_never_writes_report(tmp_path, capsys):
    csv = _csv(tmp_path)
    df = pd.read_csv(csv)
    df.loc[2, "time"] = df.loc[1, "time"]
    df.to_csv(csv, index=False)
    report = tmp_path / "shadow.json"
    assert main(["--csv", str(csv), "--report", str(report)]) == 2
    assert json.loads(capsys.readouterr().err)["status"] == "ERROR"
    assert not report.exists()


def test_cli_check_does_not_require_mlflow_or_csv(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "mlflow", None)
    monkeypatch.setitem(sys.modules, "MetaTrader5", None)
    assert main(["--check"]) == 0
    response = json.loads(capsys.readouterr().out)
    assert response["status"] == "READY_FOR_OFFLINE_RESEARCH"


def test_cli_refuses_promotion_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--promote"])
    assert exc.value.code == 2
    assert "unrecognized arguments" in capsys.readouterr().err
