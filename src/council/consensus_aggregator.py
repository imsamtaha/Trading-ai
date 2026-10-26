"""Validated PAPER recommendations; execute and broker execution always stay false."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
import json
from math import isfinite
from pathlib import Path
from typing import Mapping

CONFIG = Path(__file__).resolve().parents[2] / 'config' / 'council_role_thresholds.json'
ROLES = {'MOMENTUM', 'MEAN_REVERSION', 'NEWS_SENTIMENT'}


def number(value, name, low=0.0, high=None, *, positive=False):
    if type(value) not in (int, float) or not isfinite(value):
        raise ValueError(f'{name}: finite numeric value required')
    if value < low or (positive and value <= low) or (high is not None and value > high):
        raise ValueError(f'{name}: outside allowed range')
    return float(value)


def load_config(path=CONFIG):
    def reject(value):
        raise ValueError(f'Invalid JSON constant: {value}')
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'), parse_constant=reject)
    policy = data['policy']
    if data['schema_version'] != 2 or policy['execution_environment'] != 'PAPER' or policy['broker_execution_allowed'] is not False:
        raise ValueError('Only PAPER policy schema 2 is supported')
    if set(data['roles']) != ROLES | {'RISK_MANAGER'}:
        raise ValueError('Exactly three voting roles and RISK_MANAGER are required')
    for key in ('execution_threshold', 'max_daily_drawdown', 'max_cvar_99_pct'):
        number(policy[key], key, high=1, positive=True)
    for key in ('max_spread_pips', 'min_margin_level_pct', 'max_paper_lot_size'):
        number(policy[key], key, positive=True)
    for key in ('min_agents', 'min_roles'):
        if type(policy[key]) is not int or not 2 <= policy[key] <= 3:
            raise ValueError(f'{key}: integer quorum of 2..3 required')
    for role in ROLES:
        row = data['roles'][role]
        number(row['base_weight'], 'base_weight', high=1, positive=True)
        required = {'validation': {'min_sharpe', 'min_hit_rate', 'min_rr', 'max_mdd', 'max_ece'},
                    'demo': {'min_days', 'min_trades', 'max_mdd'},
                    'demotion': {'hard_mdd', 'kill_mdd', 'min_score', 'max_ece_drift'}}
        for section, keys in required.items():
            if set(row[section]) != keys:
                raise ValueError(f'{role}.{section}: invalid threshold schema')
            for key, value in row[section].items():
                high = 1 if any(x in key for x in ('mdd', 'hit_rate', 'ece')) else None
                number(value, f'{role}.{section}.{key}', high=high)
        if row['demotion']['kill_mdd'] < row['demotion']['hard_mdd']:
            raise ValueError('kill_mdd must not be below hard_mdd')
    if abs(sum(data['roles'][r]['base_weight'] for r in ROLES) - 1) > 1e-9:
        raise ValueError('Voting role base weights must sum to one')
    risk = data['roles']['RISK_MANAGER']
    if risk['is_veto_gate'] is not True:
        raise ValueError('Risk veto must be enabled')
    for section in ('validation', 'demo', 'demotion'):
        if not isinstance(risk[section], dict) or not risk[section]:
            raise ValueError('Missing risk thresholds')
        for key, value in risk[section].items():
            number(value, f'RISK_MANAGER.{section}.{key}')
    if policy['max_daily_drawdown'] > risk['demo']['max_daily_dd']:
        raise ValueError('Policy cannot relax the risk-manager daily drawdown limit')
    return data


class SignalAction(str, Enum):
    BUY = 'BUY'
    SELL = 'SELL'
    HOLD = 'HOLD'


class MarketRegime(str, Enum):
    TRENDING = 'trending'
    RANGING = 'ranging'
    HIGH_VOL_NEWS = 'high_volatility_news'


@dataclass(frozen=True)
class AgentVote:
    agent_id: str
    role: str
    stage: str
    signal: SignalAction
    confidence: float
    agent_score: float
    ece_error: float


@dataclass(frozen=True)
class RiskManagerState:
    daily_drawdown_pct: float
    current_spread_pips: float
    max_allowed_spread_pips: float
    margin_level_pct: float
    cvar_99_pct: float
    hard_daily_dd_limit: float = 0.03


class AtlasConsensusAggregator:
    REGIME_MULTIPLIERS = {
        MarketRegime.TRENDING: {'MOMENTUM': 1.3, 'MEAN_REVERSION': 0.2, 'NEWS_SENTIMENT': 1.0},
        MarketRegime.RANGING: {'MOMENTUM': 0.3, 'MEAN_REVERSION': 1.4, 'NEWS_SENTIMENT': 0.6},
        MarketRegime.HIGH_VOL_NEWS: {'MOMENTUM': 0.5, 'MEAN_REVERSION': 0.0, 'NEWS_SENTIMENT': 1.5},
    }

    def __init__(self, execution_threshold=None, *, config_path=CONFIG, qualifications: Mapping | None = None):
        self._config = load_config(config_path)
        self._policy = self._config['policy']
        self.execution_threshold = number(self._policy['execution_threshold'] if execution_threshold is None else execution_threshold,
                                          'execution_threshold', high=1, positive=True)
        if self.execution_threshold < self._policy['execution_threshold']:
            raise ValueError('Cannot relax the configured consensus threshold')
        # Admission records are supplied by the trusted caller, never by a vote.
        self._qualifications = deepcopy(dict(qualifications or {}))

    @staticmethod
    def _result(reason, *, action='HOLD', score=0.0, paper_lot=0.0, weights=None, gate='BLOCKED'):
        return {'execute': False, 'broker_execution_allowed': False, 'execution_environment': 'PAPER',
                'final_action': action, 'consensus_score': score, 'lot_size': 0.0,
                'suggested_paper_lot_size': paper_lot, 'active_weights': weights or {},
                'risk_gate': gate, 'reason': reason}

    def evaluate_risk_gate(self, risk):
        try:
            dd = number(risk.daily_drawdown_pct, 'drawdown', high=1)
            spread = number(risk.current_spread_pips, 'spread')
            spread_cap = number(risk.max_allowed_spread_pips, 'spread limit', positive=True)
            margin = number(risk.margin_level_pct, 'margin')
            cvar = number(risk.cvar_99_pct, 'CVaR', high=1)
            dd_cap = number(risk.hard_daily_dd_limit, 'drawdown limit', high=1, positive=True)
        except (ValueError, TypeError, AttributeError) as exc:
            return 0, f'INVALID_RISK: {exc}'
        if dd >= min(dd_cap, self._policy['max_daily_drawdown']):
            return 0, 'DAILY_DRAWDOWN_VETO'
        if cvar >= self._policy['max_cvar_99_pct']:
            return 0, 'CVAR_VETO'
        if spread > min(spread_cap, self._policy['max_spread_pips']):
            return 0, 'SPREAD_VETO'
        if margin < self._policy['min_margin_level_pct']:
            return 0, 'MARGIN_VETO'
        return 1, 'APPROVED'

    def _eligible(self, vote):
        if vote.stage not in {'PAPER', 'DEMO'}:
            raise ValueError('Only PAPER/DEMO votes are eligible')
        if vote.role not in ROLES or not isinstance(vote.agent_id, str) or not vote.agent_id.strip():
            raise ValueError('Unknown role or invalid agent identity')
        SignalAction(vote.signal)
        number(vote.confidence, 'confidence', high=1)
        number(vote.agent_score, 'agent_score', high=2, positive=True)
        number(vote.ece_error, 'ece_error', high=1)
        record = self._qualifications.get(vote.agent_id)
        if not isinstance(record, dict) or record.get('stage') != 'PAPER_APPROVED' or record.get('role') != vote.role:
            raise ValueError('Agent has no matching trusted PAPER admission')
        limits = self._config['roles'][vote.role]
        for section in ('validation', 'demo'):
            for rule, limit in limits[section].items():
                kind, metric = rule.split('_', 1)
                value = number(record[section][metric], metric,
                               high=1 if metric in {'hit_rate', 'mdd', 'ece'} else None)
                if (kind == 'min' and value < limit) or (kind == 'max' and value > limit):
                    raise ValueError(f'{section}.{metric}: qualification failed')
        current = record['current']
        score = min(number(current['score'], 'current score', high=2, positive=True), vote.agent_score)
        ece = max(number(current['ece'], 'current ECE', high=1), vote.ece_error)
        mdd = number(current['mdd'], 'current drawdown', high=1)
        drift = number(current['ece_drift'], 'ECE drift', high=1)
        if (score < limits['demotion']['min_score'] or ece > limits['validation']['max_ece']
                or mdd >= min(limits['demotion']['hard_mdd'], limits['demotion']['kill_mdd'])
                or drift > limits['demotion']['max_ece_drift']):
            raise ValueError('Agent demotion gate failed')
        return score, ece

    def compute_decision(self, votes, regime, risk_state, base_lot_size=1.0):
        approved, reason = self.evaluate_risk_gate(risk_state)
        if not approved:
            return self._result(reason)
        try:
            lot = number(base_lot_size, 'base_lot_size', high=self._policy['max_paper_lot_size'], positive=True)
            regime = MarketRegime(regime)
            if not isinstance(votes, (list, tuple)):
                raise ValueError('Votes must be a sequence')
            identities = [v.agent_id for v in votes]
            if len(set(identities)) != len(identities):
                raise ValueError('Duplicate agent identity')
            checked = [(v, *self._eligible(v)) for v in votes]
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            return self._result(f'INVALID_VOTES: {exc}')
        active = [(v, s, e) for v, s, e in checked if self.REGIME_MULTIPLIERS[regime][v.role] > 0]
        counts = Counter(v.role for v, _, _ in active)
        if len(active) < self._policy['min_agents'] or len(counts) < self._policy['min_roles']:
            return self._result('QUORUM_NOT_MET', gate='APPROVED')
        weighted_sum = total = 0.0
        weights = {}
        for v, score, ece in active:
            # An extra identity cannot multiply a role's base allocation.
            weight = self._config['roles'][v.role]['base_weight'] * score * (1 - ece) * self.REGIME_MULTIPLIERS[regime][v.role] / counts[v.role]
            direction = {SignalAction.BUY: 1, SignalAction.SELL: -1, SignalAction.HOLD: 0}[SignalAction(v.signal)]
            weighted_sum += direction * v.confidence * weight
            total += weight
            weights[v.agent_id] = weight
        if total <= 0 or not isfinite(total):
            return self._result('NO_VALID_WEIGHT')
        consensus = weighted_sum / total
        if not isfinite(consensus) or abs(consensus) > 1 + 1e-12:
            return self._result('INVALID_CONSENSUS')
        action = 'BUY' if consensus >= self.execution_threshold else 'SELL' if consensus <= -self.execution_threshold else 'HOLD'
        paper_lot = round(lot * abs(consensus), 8) if action != 'HOLD' else 0.0
        return self._result('PAPER_RECOMMENDATION', action=action, score=round(consensus, 8),
                            paper_lot=paper_lot, weights=weights, gate='APPROVED')


if __name__ == '__main__':
    config = load_config()
    print(json.dumps({'status': 'VALID', 'schema_version': config['schema_version'],
                      'execution_environment': 'PAPER', 'broker_execution_allowed': False}))
