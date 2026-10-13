"""Real model tests: invalid inputs, held-out metrics, ranking and atomic restore."""
import importlib.util
import json
import numpy as np
import pandas as pd
import pytest

@pytest.fixture(scope="module")
def pipeline():
    spec = importlib.util.find_spec("app.performance.agent_xgb")
    assert spec is not None, "AgentPerformanceXGBoost has not been integrated"
    from app.performance.agent_xgb import AgentPerformanceXGBoost
    model = AgentPerformanceXGBoost()
    X, sales, csat = model.generate_synthetic_data(400)
    model.train(X, sales, csat, source="synthetic", split="random")
    return model

def test_metrics_on_heldout_rows_and_demo_label(pipeline):
    meta = pipeline.metadata
    assert meta["source"] == "synthetic"
    assert meta["production_ready"] is False
    assert meta["rows_test"] == 80
    assert 0 <= meta["metrics"]["sales_auc"] <= 1
    assert meta["metrics"]["csat_mae"] >= 0
    assert pipeline.sales_model.n_jobs == 1

def test_scores_bounded_and_input_columns_reordered(pipeline):
    X, _, _ = pipeline.generate_synthetic_data(3)
    a = pipeline.predict_composite_score(X, .5, .5)
    b = pipeline.predict_composite_score(X[X.columns[::-1]], .5, .5)
    for left, right in zip(a, b):
        np.testing.assert_allclose(left, right)
    assert ((a[0] >= 0) & (a[0] <= 1)).all()
    assert ((a[2] >= 1) & (a[2] <= 5)).all()

@pytest.mark.parametrize("weights", [(-1, 2), (0, 0), (1, 1), (float("nan"), .5)])
def test_rejects_invalid_weights(pipeline, weights):
    X, _, _ = pipeline.generate_synthetic_data(3)
    with pytest.raises(ValueError):
        pipeline.predict_composite_score(X, *weights)

@pytest.mark.parametrize("change", ["missing", "infinite", "negative", "duplicate"])
def test_rejects_bad_features(pipeline, change):
    X, _, _ = pipeline.generate_synthetic_data(3)
    if change == "missing": X = X.drop(columns=["historical_csat"])
    elif change == "infinite": X.loc[0, "avg_handle_time_mins"] = np.inf
    elif change == "negative": X.loc[0, "current_workload"] = -1
    else: X.columns = [X.columns[0]] * len(X.columns)
    with pytest.raises(ValueError):
        pipeline.predict_composite_score(X)

def test_untrained_model_refuses_inference(pipeline):
    from app.performance.agent_xgb import AgentPerformanceXGBoost
    X, _, _ = pipeline.generate_synthetic_data(3)
    with pytest.raises(RuntimeError, match="not trained"):
        AgentPerformanceXGBoost().predict_composite_score(X)

def test_save_reload_matches_and_failed_save_preserves_previous(pipeline, tmp_path, monkeypatch):
    from app.performance.agent_xgb import AgentPerformanceXGBoost
    prefix = tmp_path / "agent"
    X, _, _ = pipeline.generate_synthetic_data(3)
    destination = pipeline.save_models(prefix)
    before = destination.read_bytes()
    restored = AgentPerformanceXGBoost.load_models(prefix)
    for a, b in zip(pipeline.predict_composite_score(X), restored.predict_composite_score(X)):
        np.testing.assert_allclose(a, b)
    def fail(*args, **kwargs): raise OSError("simulated disk failure")
    monkeypatch.setattr("app.performance.agent_xgb.os.replace", fail)
    with pytest.raises(OSError): pipeline.save_models(prefix)
    assert destination.read_bytes() == before
    assert not list(tmp_path.glob("*.tmp"))

def test_failed_retrain_keeps_working_model(pipeline):
    X, sales, csat = pipeline.generate_synthetic_data(100)
    before = pipeline.predict_composite_score(X)[0]
    with pytest.raises(ValueError):
        pipeline.train(X, np.zeros(len(X)), csat, source="observed")
    np.testing.assert_allclose(before, pipeline.predict_composite_score(X)[0])

def test_synthetic_rng_does_not_change_global_random_state(pipeline):
    np.random.seed(7)
    before = np.random.get_state()
    pipeline.generate_synthetic_data(20)
    after = np.random.get_state()
    np.testing.assert_array_equal(before[1], after[1])

def test_chronological_split_reserved_for_observed_data(pipeline):
    from app.performance.agent_xgb import AgentPerformanceXGBoost
    X, sales, csat = pipeline.generate_synthetic_data(300)
    model = AgentPerformanceXGBoost()
    model.train(X, sales, csat, source="observed", split="chronological")
    assert model.metadata["split"] == "chronological"
    assert model.metadata["rows_test"] == 60
    assert model.metadata["production_ready"] is False
    with pytest.raises(ValueError):
        model.train(X, sales[:-1], csat, source="observed")

def test_nearly_unit_weights_cannot_exceed_one(pipeline):
    from app.performance.agent_xgb import AgentPerformanceXGBoost
    model=AgentPerformanceXGBoost()
    X,sales,_=model.generate_synthetic_data(100)
    model.train(X,sales,np.full(len(X),5.),source="synthetic",split="random")
    scores,_,_=model.predict_composite_score(X,1e-6,1)
    assert (scores<=1).all()

def test_nonfinite_saved_metadata_refused(pipeline,tmp_path):
    from app.performance.agent_xgb import AgentPerformanceXGBoost
    import zipfile
    prefix=tmp_path/"agent"
    path=pipeline.save_models(prefix)
    with zipfile.ZipFile(path) as bundle:
        data={name:bundle.read(name) for name in bundle.namelist()}
    meta=json.loads(data["metadata.json"])
    meta["metrics"]["sales_auc"]=float("nan")
    data["metadata.json"]=json.dumps(meta).encode()
    with zipfile.ZipFile(path,"w") as bundle:
        for name,content in data.items(): bundle.writestr(name,content)
    with pytest.raises(ValueError):
        AgentPerformanceXGBoost.load_models(prefix)

def test_values_outside_xgboost_float_range_refused(pipeline):
    X,_,_=pipeline.generate_synthetic_data(3)
    X.loc[0,"avg_handle_time_mins"]=1e100
    with pytest.raises(ValueError):
        pipeline.predict_composite_score(X)
