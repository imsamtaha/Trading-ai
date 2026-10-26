"""Offline confidence calibration using quote-backed, settled PAPER setups.

No terminal, broker, network or execution imports. Model selection uses validation;
the final chronological holdout is used once to decide whether to accept a model.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import exp, isfinite, log
from pathlib import Path

NON_DIRECTIONAL = {'risk_executive', 'recovery_guardian', 'macro_analyst'}
MIN_IMPROVEMENT = 0.005


def finite(value, name, *, low=None, high=None):
    if type(value) not in (float, int) or not isfinite(value):
        raise ValueError(f'{name}: finite numeric value required')
    if (low is not None and value < low) or (high is not None and value > high):
        raise ValueError(f'{name}: outside allowed range')
    return float(value)


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('Timestamp must be an ISO string')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Explicit timezone required')
    return result.astimezone(timezone.utc)


def read_json(path, *, lines=False):
    raw = Path(path).read_bytes()
    def reject(value):
        raise ValueError(f'Non-finite JSON constant: {value}')
    text = raw.decode('utf-8-sig')
    data = [json.loads(x, parse_constant=reject) for x in text.splitlines() if x.strip()] if lines else json.loads(text, parse_constant=reject)
    return data, sha256(raw).hexdigest()


def observed_examples(journal_path, ledger_path, *, now=None, max_quote_age=60):
    now = now or datetime.now(timezone.utc)
    finite(max_quote_age, 'max_quote_age', low=0.001, high=300)
    journal, journal_hash = read_json(journal_path, lines=True)
    ledger, ledger_hash = read_json(ledger_path)
    trades = ledger['closed_trades']
    by_snapshot = {}
    for trade in trades:
        key = trade.get('training_context', {}).get('council', {}).get('snapshot_id')
        if key:
            if key in by_snapshot:
                raise ValueError('Duplicate settled snapshot in ledger')
            by_snapshot[key] = trade
    seen, accepted, excluded = set(), [], Counter()
    flagged = Counter()
    for row in journal:
        key = row['snapshot_id']
        if not isinstance(key, str) or not key or key in seen:
            raise ValueError('Invalid or duplicate journal snapshot')
        seen.add(key)
        if row.get('execution_environment') != 'PAPER' or row.get('broker_execution_allowed') is not False:
            raise ValueError('Explicit PAPER-only journal provenance required')
        trade = by_snapshot.get(key)
        if trade is None:
            excluded['missing_settled_trade'] += 1
            continue
        card = trade.get('quality_card', {})
        if card.get('source') != 'MT5' or not all(k in trade for k in ('entry_quote', 'exit_quote')):
            excluded['missing_mt5_quote_evidence'] += 1
            continue
        context = trade['training_context']
        intent = context['trade_intent']
        if (intent.get('execution_environment') != 'PAPER' or intent.get('broker_execution_allowed') is not False
                or card.get('broker_execution_allowed') is not False or intent.get('snapshot_id') != key):
            raise ValueError('Ledger PAPER provenance mismatch')
        if trade.get('status') != 'CLOSED':
            raise ValueError('Training outcome must be closed')
        opened, closed = timestamp(trade['opened_at']), timestamp(trade['closed_at'])
        recorded = timestamp(row['timestamp'])
        if not opened < closed <= recorded <= now:
            raise ValueError('Unsettled outcome or invalid event chronology')
        offset = finite(card['quote_offset_seconds'], 'recorded broker clock offset', low=-50400, high=50400)
        stale = False
        for qkey, event in (('entry_quote', opened), ('exit_quote', closed)):
            quote = trade[qkey]
            bid = finite(quote['bid'], 'bid', low=0.000000001)
            ask = finite(quote['ask'], 'ask', low=bid)
            tick = finite(quote.get('time_msc', quote['time'] * 1000), 'quote timestamp', low=1) / 1000 - offset
            age = event.timestamp() - tick
            if not -2 <= age <= max_quote_age:
                stale = True
        if stale:
            excluded['stale_or_future_quote'] += 1
            continue
        direction = {'LONG': 'BUY', 'SHORT': 'SELL'}.get(trade['direction'])
        if direction is None:
            raise ValueError('Invalid settled trade direction')
        r = finite(trade['r_multiple'], 'settled R multiple')
        realized = direction if r > 0 else ('SELL' if direction == 'BUY' else 'BUY') if r < 0 else 'HOLD'
        if row['realized_direction'] != realized:
            raise ValueError('Journal label does not match settled ledger outcome')
        originals = context['council']['opinions']
        original_by_agent = {v['agent']: v for v in originals}
        if len(original_by_agent) != len(originals):
            raise ValueError('Duplicate agent in original council snapshot')
        opinions, identities = [], set()
        for opinion in row['opinions']:
            agent = opinion['agent']
            if not isinstance(agent, str) or not agent.strip() or agent in identities:
                raise ValueError('Invalid or duplicate agent in training snapshot')
            identities.add(agent)
            if agent in NON_DIRECTIONAL:
                continue
            original = original_by_agent.get(agent)
            p = finite(opinion['confidence'], 'confidence', low=0, high=1)
            decision = opinion['decision']
            if (decision not in {'BUY', 'SELL', 'HOLD'} or original is None
                    or decision != original['decision'] or p != original['confidence']):
                raise ValueError('Training prediction differs from original entry evidence')
            opinions.append({'agent': agent, 'p': p, 'y': float(decision == realized)})
        if not opinions:
            excluded['no_directional_agents'] += 1
            continue
        flagged.update(card.get('flags', []))
        accepted.append({'snapshot_id': key, 'opened_at': opened, 'label_available_at': recorded,
                         'symbol': trade['symbol'], 'opinions': opinions})
    accepted.sort(key=lambda r: (r['opened_at'], r['snapshot_id']))
    return accepted, {'source': 'MT5_OBSERVED_PAPER', 'journal_sha256': journal_hash,
                      'ledger_sha256': ledger_hash, 'journal_rows': len(journal),
                      'accepted_setups': len(accepted), 'excluded': dict(excluded),
                      'accepted_quality_flags': dict(flagged), 'max_quote_age_seconds': max_quote_age,
                      'broker_fills_verified': False,
                      'label': 'correctness of original directional opinion versus settled paper outcome'}


def chronological_split(rows):
    rows = sorted(rows, key=lambda r: (r['opened_at'], r['snapshot_id']))
    bounds = [i for i in range(1, len(rows)) if rows[i]['opened_at'] != rows[i-1]['opened_at']]
    if len(bounds) < 2:
        raise ValueError('At least three distinct prediction times required')
    a = min(bounds[:-1], key=lambda x: (abs(x-len(rows)*0.6), x))
    b = min((x for x in bounds if x > a), key=lambda x: (abs(x-len(rows)*0.8), x))
    train = [r for r in rows[:a] if r['label_available_at'] < rows[a]['opened_at']]
    validation = [r for r in rows[a:b] if r['label_available_at'] < rows[b]['opened_at']]
    return train, validation, rows[b:], len(rows)-len(train)-len(validation)-len(rows[b:])


def sigmoid(x):
    return 1 / (1 + exp(-max(-40, min(40, x))))


def logit(p):
    p = max(1e-6, min(1-1e-6, p))
    return log(p / (1-p))


def predict(model, p):
    return sigmoid(model['intercept'] + model['slope'] * logit(p))


def fit_logistic(rows, regularization):
    # Monotonic Platt calibration. Fixed optimizer; validation selects shrinkage.
    a, b = 0.0, 1.0
    features = [(logit(r['p']), r['y']) for r in rows]
    scale = max(1.0, sum(x*x for x, _ in features) / len(features))
    rate = 0.5 / scale
    for _ in range(2000):
        errors = [(sigmoid(a+b*x)-y, x) for x, y in features]
        ga = sum(e for e, _ in errors) / len(errors)
        gb = sum(e*x for e, x in errors) / len(errors) + regularization * (b-1)
        a -= rate * ga
        b = max(0.0, min(10.0, b-rate*gb))
    return {'method': 'monotonic_platt', 'intercept': a, 'slope': b, 'regularization': regularization}


def brier(rows, predict_fn):
    return sum((predict_fn(r['p'])-r['y'])**2 for r in rows) / len(rows)


def train_observed(journal_path, ledger_path, *, now=None):
    now = now or datetime.now(timezone.utc)
    setups, provenance = observed_examples(journal_path, ledger_path, now=now)
    if not setups:
        raise ValueError('No settled quote-backed PAPER examples available')
    by_agent = defaultdict(list)
    for setup in setups:
        for opinion in setup['opinions']:
            by_agent[opinion['agent']].append({**{k: setup[k] for k in ('snapshot_id', 'opened_at', 'label_available_at')}, **opinion})
    agents = {}
    for agent, rows in sorted(by_agent.items()):
        entry = {'samples': len(rows), 'weight': 1.0, 'locked_baseline': True, 'accepted': False}
        agents[agent] = entry
        try:
            train, val, test, purged = chronological_split(rows)
        except ValueError as exc:
            entry['reason'] = str(exc)
            continue
        entry.update({'rows_train': len(train), 'rows_validation': len(val), 'rows_test': len(test), 'rows_purged': purged,
                      'time_ranges': {name: {'start': part[0]['opened_at'].isoformat(), 'end': part[-1]['opened_at'].isoformat()}
                                      for name, part in (('train',train), ('validation',val), ('test',test)) if part}})
        if len(train) < 20 or min(len(val), len(test)) < 10 or len({r['y'] for r in train}) < 2:
            entry['reason'] = 'INSUFFICIENT_SETTLED_PARTITIONS_OR_CLASSES'
            continue
        models = [fit_logistic(train, strength) for strength in (0.001, 0.01, 0.1, 1.0)]
        model = min(models, key=lambda m: brier(val, lambda p: predict(m, p)))
        prior = (sum(r['y'] for r in train)+1)/(len(train)+2)
        metrics = {}
        for name, part in (('validation', val), ('test', test)):
            raw = brier(part, lambda p: p)
            constant = brier(part, lambda p: prior)
            calibrated = brier(part, lambda p: predict(model, p))
            metrics[name] = {'raw_brier': raw, 'train_prior_brier': constant, 'calibrated_brier': calibrated,
                             'improvement_vs_raw': raw-calibrated,
                             'improvement_vs_stronger_baseline': min(raw,constant)-calibrated}
        accepted = all(metrics[p]['improvement_vs_stronger_baseline'] >= MIN_IMPROVEMENT for p in ('validation','test'))
        entry.update({'model': model, 'metrics': metrics, 'accepted': accepted, 'locked_baseline': not accepted,
                      'reason': 'PAPER_CALIBRATION_ACCEPTED' if accepted else 'HOLD_BASELINE', 'train_prior': prior})
    return {'version': 2, 'generated_at': now.isoformat(), 'training_environment': 'PAPER',
            'broker_execution_allowed': False, 'total_examples': len(setups), 'provenance': provenance,
            'minimum_brier_improvement': MIN_IMPROVEMENT, 'agents': agents,
            'accepted_agents': [a for a, value in agents.items() if value['accepted']],
            'policy': 'No live promotion; no role relabeling; risk and regime agents are excluded.'}


def calibrated_confidence(profile, agent, confidence):
    """Validated version-2 inference; invalid/unaccepted profiles retain baseline."""
    base = finite(confidence, 'confidence', low=0, high=1)
    try:
        if (agent in NON_DIRECTIONAL or profile.get('version') != 2
                or profile.get('training_environment') != 'PAPER' or profile.get('broker_execution_allowed') is not False):
            return base
        row = profile['agents'][agent]
        if row['accepted'] is not True or row['locked_baseline'] is not False:
            return base
        for partition in ('validation', 'test'):
            finite(row['metrics'][partition]['improvement_vs_stronger_baseline'], 'improvement', low=MIN_IMPROVEMENT)
        model = row['model']
        if model['method'] != 'monotonic_platt':
            return base
        finite(model['intercept'], 'intercept', low=-100, high=100)
        finite(model['slope'], 'slope', low=0, high=10)
        return predict(model, base)
    except (AttributeError, KeyError, TypeError, ValueError):
        return base
