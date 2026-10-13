"""Explicit offline training: demo data or time-ordered observed CSV."""
import argparse
import json
from pathlib import Path

from app.performance.agent_xgb import AgentPerformanceXGBoost, FEATURES


def main():
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--demo", action="store_true")
    source.add_argument("--csv", type=Path)
    parser.add_argument("--output-prefix", type=Path)
    args = parser.parse_args()
    model = AgentPerformanceXGBoost()
    prefix = args.output_prefix or Path(__file__).parent / ".runtime/models/agent_performance"
    if args.demo:
        X, sales, csat = model.generate_synthetic_data()
        model.train(X, sales, csat, source="synthetic", split="random")
        prefix = Path(str(prefix) + "_demo")
    else:
        import pandas as pd
        frame = pd.read_csv(args.csv)
        required = set(FEATURES) | {"sale_success", "csat_outcome", "occurred_at"}
        if not required.issubset(frame.columns):
            parser.error("CSV needs features, sale_success, csat_outcome and occurred_at")
        frame["occurred_at"] = pd.to_datetime(frame["occurred_at"], utc=True, errors="raise")
        if frame["occurred_at"].isna().any() or frame["occurred_at"].duplicated().any():
            parser.error("occurred_at must be present and unique for chronological boundaries")
        frame = frame.sort_values("occurred_at", kind="stable")
        model.train(frame[list(FEATURES)], frame.sale_success, frame.csat_outcome,
                    source="observed", split="chronological")
    saved = model.save_models(prefix)
    restored = AgentPerformanceXGBoost.load_models(prefix)
    example = model.generate_synthetic_data(3)[0]
    import numpy as np
    np.testing.assert_allclose(model.predict_composite_score(example)[0],
                               restored.predict_composite_score(example)[0])
    print(json.dumps({"bundle": str(saved), "metadata": restored.metadata}, indent=2))


if __name__ == "__main__":
    main()
