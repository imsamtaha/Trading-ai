"""Explicit offline specialist training; never adjusts execution permissions."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--role', choices=['macro_analyst', 'quantitative_strategist'], required=True)
    parser.add_argument('--csv', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT/'.runtime/models/council')
    parser.add_argument('--confirmed-observed', action='store_true', required=True)
    args = parser.parse_args()
    from app.performance.training_lock import training_lock
    from app.intelligence.specialist_training import SpecialistModel
    import pandas as pd
    with training_lock(args.output/args.role):
        frame = pd.read_csv(args.csv)
        model = SpecialistModel(args.role)
        metadata = model.fit(frame, confirmed_observed=args.confirmed_observed)
        path = model.save(args.output)
        # Validate the exact native artifact before reporting success.
        SpecialistModel.load(args.output, args.role)
    print(json.dumps({'role':args.role,'bundle':str(path),'metadata':metadata},allow_nan=False))


if __name__ == '__main__':
    main()
