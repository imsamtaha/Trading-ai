"""Strict point-in-time bars. time is explicitly the bar-close timestamp."""
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import fsum

from .core import number


def timestamp(value):
    if not isinstance(value, str): raise ValueError('Timestamp must be ISO 8601 text')
    value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if value.tzinfo is None: raise ValueError('Timestamp must include timezone')
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class Bar:
    time: datetime
    available_at: datetime
    open: float
    high: float
    low: float
    close: float
    spread_bps: float
    slippage_bps: float
    fee_bps: float

    def __post_init__(self):
        if self.time.tzinfo is None or self.available_at.tzinfo is None or self.available_at < self.time:
            raise ValueError('Invalid point-in-time timestamp')
        prices = [number(getattr(self, k), k, 1e-9, 1e12) for k in ('open', 'high', 'low', 'close')]
        if self.low > min(self.open, self.close) or self.high < max(self.open, self.close) or self.low > self.high:
            raise ValueError('Inconsistent OHLC')
        for k in ('spread_bps', 'slippage_bps', 'fee_bps'): number(getattr(self, k), k, 0, 10000)


def load_bars(path):
    with open(path, newline='', encoding='utf8') as handle:
        reader = csv.DictReader(handle)
        required = set(Bar.__dataclass_fields__)
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('CSV requires time,available_at,open,high,low,close,spread_bps,slippage_bps,fee_bps')
        bars = []
        for row in reader:
            bars.append(Bar(timestamp(row['time']), timestamp(row['available_at']),
                            *(float(row[k]) for k in ('open','high','low','close','spread_bps','slippage_bps','fee_bps'))))
    if len(bars) < 50 or any(a.time >= b.time for a,b in zip(bars,bars[1:])):
        raise ValueError('Need >=50 strictly chronological unique bars, one symbol/timeframe per CSV')
    return bars


def feature_snapshot(bars, index):
    if not 20 <= index < len(bars): raise ValueError('Need 20 prior bars')
    decision_time = bars[index].time
    window = bars[index-20:index+1]
    if any(b.available_at > decision_time for b in window):
        raise ValueError('Feature not yet available at decision time')
    closes = [b.close for b in window]
    sma = fsum(closes[-20:])/20
    tr = [max(b.high-b.low, abs(b.high-a.close), abs(b.low-a.close)) for a,b in zip(window,window[1:])]
    atr = fsum(tr[-14:])/14
    if atr <= 0: raise ValueError('Zero volatility is not a valid sizing input')
    prior_high = max(b.high for b in window[:-1])
    prior_low = min(b.low for b in window[:-1])
    z = (closes[-1]-sma)/atr
    features = {'close':closes[-1], 'sma20':sma, 'atr14':atr, 'normalized_deviation':z,
                'prior_high':prior_high, 'prior_low':prior_low}
    encoded = json.dumps({'time':decision_time.isoformat(),'features':features},sort_keys=True,allow_nan=False).encode()
    # Untrained hypotheses only: no expected edge/confidence is fabricated here.
    sleeves = {
        'trend': 1 if z > .5 else -1 if z < -.5 else 0,
        'mean_reversion': -1 if z > 1.5 else 1 if z < -1.5 else 0,
        'breakout': 1 if closes[-1] > prior_high else -1 if closes[-1] < prior_low else 0,
    }
    return {'time':decision_time.isoformat(),'features':features,'feature_hash':sha256(encoded).hexdigest(),
            'sleeves':sleeves,'status':'UNVALIDATED_HYPOTHESES','broker_execution_allowed':False}


def round_trip_cost_r(bar, entry, stop_distance):
    entry = number(entry,'entry',1e-9,1e12)
    stop_distance = number(stop_distance,'stop_distance',1e-9,1e12)
    # All input bps are ROUND-TRIP totals, not per-side values.
    return entry*(bar.spread_bps+bar.slippage_bps+bar.fee_bps)/10000/stop_distance


def triple_barrier(bars, index, side, stop_distance, target_r=2.0, horizon=10):
    if type(side) is not int or side not in (-1,1): raise ValueError('side must be -1 or 1')
    if type(horizon) is not int or horizon < 1 or index < 0 or index+horizon >= len(bars):
        raise ValueError('Unresolved outcome horizon')
    stop_distance=number(stop_distance,'stop_distance',1e-9,1e12)
    target_r=number(target_r,'target_r',1e-9,100)
    entry=bars[index+1].open  # A signal at close can only fill on the next bar.
    stop, target = entry-side*stop_distance, entry+side*target_r*stop_distance
    if min(stop,target)<=0: raise ValueError('Invalid nonpositive barrier price')
    exit_price, reason, end = bars[index+horizon].close, 'TIME', index+horizon
    for j in range(index+1,index+horizon+1):
        b=bars[j]
        if side*(b.open-stop) <= 0:
            exit_price,reason,end=b.open,'STOP_GAP',j;break
        stop_hit = b.low <= stop if side==1 else b.high >= stop
        target_hit = b.high >= target if side==1 else b.low <= target
        if stop_hit: # Conservative stop-first when both barriers touch within one bar.
            exit_price,reason,end=stop,'STOP',j;break
        if target_hit:
            exit_price,reason,end=target,'TARGET',j;break
    gross=side*(exit_price-entry)/stop_distance
    cost=round_trip_cost_r(bars[index+1],entry,stop_distance)
    return {'gross_r':gross,'cost_r':cost,'net_r':gross-cost,'label':int(gross-cost>0),
            'entry_index':index+1,'end_index':end,'reason':reason,'decision_index':index,
            'label_available_at':max(b.available_at for b in bars[index+1:end+1]).isoformat(),
            'source':'OHLC_COUNTERFACTUAL','broker_execution_allowed':False}
