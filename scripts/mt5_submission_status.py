"""Inspect/reconcile delivery evidence without sending or closing orders."""
import argparse
import json
from pathlib import Path
import sys
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reconcile', action='store_true',
                        help='Read exact completed order/deal evidence; never retry delivery.')
    args = parser.parse_args(argv)
    load_dotenv(ROOT / '.env')
    broker = MT5Broker(MT5Config.from_env())
    try:
        report = broker.reconcile_submissions() if args.reconcile else broker.submission_status()
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
        return 2 if report['blocked'] else 0
    except MT5ExecutionError as exc:
        print(json.dumps({'blocked': True, 'error': str(exc)}))
        return 3
    finally:
        broker.disconnect()


if __name__ == '__main__':
    raise SystemExit(main())
