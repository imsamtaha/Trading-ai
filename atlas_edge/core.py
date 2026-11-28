from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Any

VERSION = '3.0-research.1'


def number(value: Any, name: str, low=None, high=None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    result = float(value)
    if low is not None and result < low or high is not None and result > high:
        raise ValueError(f'{name} outside bounds')
    return result


def policy():
    return {
        'version': VERSION, 'stage': 'RESEARCH_ONLY', 'default_decision': 'ABSTAIN',
        'execution_environment': 'PAPER', 'broker_execution_allowed': False,
        'live_activation_allowed': False, 'existing_risk_authority': 'UNCHANGED',
        'required_reviews': ['STC-04', 'STC-09'],
        'minimum_resolved_oos_decisions': 200,
        'required_baselines': ['cash', 'trend', 'random', 'v2_1'],
        'cost_stress_multipliers': [1.0, 1.5, 2.0],
        'research_hurdle_r': .05,
        'implemented': ['point_in_time_validation', 'triple_barrier_labels', 'explicit_costs_r',
                        'purged_walk_forward', 'paired_block_bootstrap', 'multiple_trial_correction',
                        'calibration_metrics', 'ev_gate', 'capped_sizing', 'research_registry'],
        'not_verified': ['profitable_alpha', 'trained_meta_labeler', 'regime_model_oos_improvement',
                         'decorrelated_allocator', 'rescue_exit_model', 'runtime_worker',
                         'unattended_provider_integrations', 'execution_gateway_v2_1_installation'],
    }


@dataclass(frozen=True)
class EdgeEvidence:
    # These are independently validated estimates; this gate does not manufacture them.
    probability: float
    probability_lower: float
    average_win_gross_r: float
    average_loss_gross_r: float
    spread_r: float
    slippage_r: float
    fees_r: float
    ev_lower_r: float
    target_volatility: float
    instrument_volatility: float
    drawdown: float
    risk_ceiling: float
    risk_approval: str
    resolved_oos: int
    model_version: str
    feature_hash: str
    data_fresh: bool
    model_validated: bool
    source: str = 'QUANT'


def evaluate_edge(e: EdgeEvidence) -> dict:
    result = {'version': VERSION, 'decision': 'ABSTAIN', 'risk_fraction': 0.0,
              'execution_environment': 'PAPER', 'broker_execution_allowed': False,
              'live_activation_allowed': False, 'reason_codes': []}
    try:
        p = number(e.probability, 'probability', 0, 1)
        p_low = number(e.probability_lower, 'probability_lower', 0, p)
        win = number(e.average_win_gross_r, 'average_win_gross_r', 0, 1000)
        loss = number(e.average_loss_gross_r, 'average_loss_gross_r', 1e-9, 1000)
        costs = sum(number(v, k, 0, 1000) for k, v in (
            ('spread', e.spread_r), ('slippage', e.slippage_r), ('fees', e.fees_r)))
        lower = number(e.ev_lower_r, 'ev_lower', -1000, 1000)
        vol = number(e.instrument_volatility, 'volatility', 1e-9, 1000)
        target = number(e.target_volatility, 'target_volatility', 1e-9, 1000)
        dd = number(e.drawdown, 'drawdown', 0, 1)
        ceiling = number(e.risk_ceiling, 'risk_ceiling', 0, .02)
        if type(e.resolved_oos) is not int or e.resolved_oos < 0:
            raise ValueError('resolved_oos must be an integer')
        if type(e.data_fresh) is not bool or type(e.model_validated) is not bool:
            raise ValueError('explicit boolean evidence required')
        if not isinstance(e.model_version, str) or not e.model_version.strip():
            raise ValueError('missing model version')
        if not isinstance(e.feature_hash, str) or len(e.feature_hash) != 64 or any(c not in '0123456789abcdef' for c in e.feature_hash):
            raise ValueError('missing feature hash')
        ev = p * win - (1-p) * loss - costs
        if lower > ev:
            raise ValueError('lower bound exceeds point estimate')
    except (ValueError, TypeError, OverflowError):
        result['reason_codes'] = ['MALFORMED_EVIDENCE']
        return result
    reasons = result['reason_codes']
    result.update(expected_net_r=ev, expected_cost_r=costs, ev_lower_r=lower)
    if e.source != 'QUANT': reasons.append('LLM_DIRECTION_NOT_ALLOWED')
    if not e.data_fresh: reasons.append('STALE_DATA')
    if not e.model_validated: reasons.append('MODEL_NOT_OOS_VALIDATED')
    if e.resolved_oos < 200: reasons.append('INSUFFICIENT_RESOLVED_OOS')
    if e.risk_approval != 'RISK_ACCEPTABLE': reasons.append('SENIOR_RISK_NOT_APPROVED')
    if ev <= .05 or lower <= 0: reasons.append('NO_POSITIVE_NET_EDGE')
    # Effective hurdle tightens as probability uncertainty grows; never decreases .05R.
    hurdle = .05 + (p-p_low) * (win+loss)
    result['hurdle_r'] = hurdle
    if ev <= hurdle and 'NO_POSITIVE_NET_EDGE' not in reasons: reasons.append('UNCERTAINTY_HURDLE')
    # Quarter-Kelly uses a conservative lower-bound payoff ratio after expected costs.
    net_win, net_loss = win-costs, loss+costs
    kelly = max(0.0, p_low-(1-p_low)*net_loss/net_win) if net_win > 0 else 0.0
    risk = min(ceiling, .25*kelly, ceiling*min(1.0, target/vol)) * max(0.0, 1-dd/.20)
    if risk <= 0: reasons.append('ZERO_RISK_BUDGET')
    if not reasons:
        result.update(decision='RESEARCH_CANDIDATE', risk_fraction=risk)
        reasons.append('REQUIRES_PAPER_GATE_AND_INDEPENDENT_REVIEW')
    return result
