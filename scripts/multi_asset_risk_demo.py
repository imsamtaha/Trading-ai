"""The supplied gold example under paper assumptions; never connects to MT5."""
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.risk.multi_asset import MultiAssetRiskEngine

if __name__ == '__main__':
    result=MultiAssetRiskEngine(100000).calculate_position('XAUUSD',2650,2635,80000)
    print(json.dumps(result,indent=2,allow_nan=False))
