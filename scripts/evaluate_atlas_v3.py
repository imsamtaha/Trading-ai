"""Write offline v3 research evidence without changing Council, risk or broker state."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from atlas_edge.data import load_bars
from atlas_edge.research import evaluate_research
from atlas_edge.registry import register_challenger


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-kind',required=True,choices=['synthetic','historical'])
    parser.add_argument('--source-label',required=True,help='User-declared dataset source; not independent attestation')
    parser.add_argument('--csv',required=True,type=Path)
    parser.add_argument('--sleeve',choices=['trend','mean_reversion','breakout'],default='trend')
    parser.add_argument('--horizon',type=int,default=10)
    parser.add_argument('--folds',type=int,default=3)
    parser.add_argument('--trials',type=int,required=True,help='Total configurations tried, including unsuccessful trials')
    parser.add_argument('--v2-baseline',type=Path,help='JSON mapping timezone-aware decision close-time ISO timestamps (matched by instant) to saved v2.1 sides (-1/0/1)')
    parser.add_argument('--registry',type=Path,help='Optional separate research-only challenger registry JSON')
    parser.add_argument('--output',type=Path,default=Path('data/atlas_edge_v3_report.json'))
    args=parser.parse_args()
    try:
        old=json.loads(args.v2_baseline.read_text()) if args.v2_baseline else None
        if old is not None and not isinstance(old,dict): raise ValueError('Invalid v2 baseline mapping')
        report=evaluate_research(load_bars(args.csv),sleeve=args.sleeve,horizon=args.horizon,
                                 folds=args.folds,trials=args.trials,old_council=old,input_kind='SYNTHETIC' if args.data_kind=='synthetic' else 'HISTORICAL_USER_SUPPLIED',source_label=args.source_label)
        report['generated_at']=datetime.now(timezone.utc).isoformat()
        if args.registry: register_challenger(report,args.registry)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        fd,path=tempfile.mkstemp(dir=args.output.parent,prefix='.edge-v3-',suffix='.json')
        try:
            with os.fdopen(fd,'w') as handle: json.dump(report,handle,indent=2,allow_nan=False)
            os.replace(path,args.output)
        finally:
            if os.path.exists(path): os.unlink(path)
    except (OSError,ValueError,KeyError,TypeError,OverflowError) as exc:
        parser.error(str(exc))
    print(json.dumps({'status':report['status'],'stage':'RESEARCH_ONLY','model_id':report['model_id'],
                      'sample_count':report['sample_count'],'report':str(args.output),
                      'broker_execution_allowed':False,'champion_unchanged':True}))
    return 0


if __name__=='__main__': raise SystemExit(main())
