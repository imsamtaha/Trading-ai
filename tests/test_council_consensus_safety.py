from copy import deepcopy
from dataclasses import replace
import json

import pytest

from src.council.consensus_aggregator import (
    AgentVote, AtlasConsensusAggregator, MarketRegime, RiskManagerState, SignalAction, load_config,
)


def qualification(role):
    return {'role': role, 'stage': 'PAPER_APPROVED',
            'validation': {'sharpe': 2, 'hit_rate': .8, 'rr': 3, 'mdd': .01, 'ece': .01},
            'demo': {'days': 35, 'trades': 150, 'mdd': .01},
            'current': {'score': 1, 'ece': .01, 'mdd': .01, 'ece_drift': .01}}


@pytest.fixture
def setup():
    votes = [AgentVote('a', 'MOMENTUM', 'PAPER', SignalAction.BUY, .8, 1, .01),
             AgentVote('b', 'NEWS_SENTIMENT', 'PAPER', SignalAction.BUY, .8, 1, .01)]
    registry = {v.agent_id: qualification(v.role) for v in votes}
    return AtlasConsensusAggregator(qualifications=registry), votes, RiskManagerState(.01, 1, 2, 400, .01), registry


def evaluate(setup, **kwargs):
    engine, votes, risk, _ = setup
    return engine.compute_decision(kwargs.pop('votes', votes), kwargs.pop('regime', MarketRegime.TRENDING),
                                   kwargs.pop('risk', risk), **kwargs)


def test_valid_consensus_is_a_paper_recommendation_only(setup, monkeypatch):
    monkeypatch.setenv('ATLAS_CI_DRY_RUN', 'false')
    monkeypatch.setenv('MT5_READONLY_MODE', 'false')
    result = evaluate(setup)
    assert result['final_action'] == 'BUY'
    assert result['suggested_paper_lot_size'] == .8
    assert result['execute'] is result['broker_execution_allowed'] is False
    assert result['lot_size'] == 0
    assert result['risk_gate'] == 'APPROVED'


@pytest.mark.parametrize('field', list(RiskManagerState.__dataclass_fields__))
@pytest.mark.parametrize('bad', [float('nan'), float('inf'), -1, True, '0.01'])
def test_invalid_risk_is_rejected(setup, field, bad):
    result = evaluate(setup, risk=replace(setup[2], **{field: bad}))
    assert result['final_action'] == 'HOLD'
    assert result['risk_gate'] == 'BLOCKED'
    assert result['reason'].startswith('INVALID_RISK')


@pytest.mark.parametrize('changes,reason', [
    ({'cvar_99_pct': .03}, 'CVAR_VETO'),
    ({'daily_drawdown_pct': .2, 'hard_daily_dd_limit': .5}, 'DAILY_DRAWDOWN_VETO'),
    ({'current_spread_pips': 3, 'max_allowed_spread_pips': 10}, 'SPREAD_VETO'),
    ({'margin_level_pct': 149}, 'MARGIN_VETO'),
])
def test_caller_cannot_relax_policy(setup, changes, reason):
    assert evaluate(setup, risk=replace(setup[2], **changes))['reason'] == reason


@pytest.mark.parametrize('lot', [-1, 0, 2, float('nan'), float('inf'), True])
def test_invalid_lot_rejected(setup, lot):
    assert evaluate(setup, base_lot_size=lot)['final_action'] == 'HOLD'


@pytest.mark.parametrize('changes', [{'confidence': 2}, {'confidence': -.5}, {'confidence': float('nan')},
    {'agent_score': -.5}, {'agent_score': .01}, {'ece_error': .9}, {'ece_error': -.1},
    {'stage': 'LIVE_EXECUTION'}, {'role': 'UNKNOWN'}, {'signal': 'INVALID'}])
def test_invalid_or_unqualified_vote_rejected(setup, changes):
    votes = [replace(setup[1][0], **changes), setup[1][1]]
    assert evaluate(setup, votes=votes)['final_action'] == 'HOLD'


def test_duplicate_identity_cannot_change_consensus(setup):
    assert 'Duplicate' in evaluate(setup, votes=setup[1]+[setup[1][0]])['reason']


def test_single_vote_and_unknown_registry_fail_closed(setup):
    assert evaluate(setup, votes=setup[1][:1])['reason'] == 'QUORUM_NOT_MET'
    result = AtlasConsensusAggregator().compute_decision(setup[1], MarketRegime.TRENDING, setup[2])
    assert result['final_action'] == 'HOLD'


def test_demo_and_validation_thresholds_are_enforced(setup):
    _, votes, risk, registry = setup
    for section, metric, value in [('demo','days',1), ('demo','trades',1), ('validation','rr',.1),
                                   ('current','mdd',.1), ('current','ece_drift',.9)]:
        records = deepcopy(registry)
        records['a'][section][metric] = value
        result = AtlasConsensusAggregator(qualifications=records).compute_decision(votes, MarketRegime.TRENDING, risk)
        assert result['final_action'] == 'HOLD'


def test_registry_is_copied_and_schema_is_required(setup, tmp_path):
    setup[3]['a']['current']['score'] = .01
    assert evaluate(setup)['final_action'] == 'BUY'
    config = load_config()
    del config['roles']['MOMENTUM']['demo']['min_days']
    path = tmp_path/'config.json'
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError):
        AtlasConsensusAggregator(config_path=path)


def test_consensus_threshold_cannot_be_disabled():
    for value in (0, -.1, .1, 2, float('nan')):
        with pytest.raises(ValueError):
            AtlasConsensusAggregator(value)
