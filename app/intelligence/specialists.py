"""Separated analytical roles and a deterministic, non-voting risk authority."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from math import isclose, isfinite
from typing import Any, Mapping

from app.intelligence.council import AgentOpinion

CONTRACTS = {
    "macro_analyst": {
        "name": "The Macro Analyst", "authority": "REGIME_CONTEXT",
        "training_target": "structural_regime",
        "features": ["policy_rate_change", "inflation_surprise", "order_flow_imbalance"],
        "model_file": "macro_analyst.bundle.zip", "learned_weight_allowed": True,
    },
    "quantitative_strategist": {
        "name": "The Quantitative Strategist", "authority": "ENTRY_PROPOSAL",
        "training_target": "net_return_r",
        "features": ["trend_strength", "momentum_score", "price_action_score", "spread_zscore", "transaction_cost_bps"],
        "model_file": "quantitative_strategist.bundle.zip", "learned_weight_allowed": True,
    },
    "risk_executive": {
        "name": "The Risk Executive", "authority": "ABSOLUTE_VETO",
        "training_target": None, "features": [], "model_file": None,
        "learned_weight_allowed": False,
        "checks": ["position_sizing", "correlation_limits", "stop_losses"],
    },
}


def specialist_contracts():
    return deepcopy(CONTRACTS)


def timestamp(value):
    result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timezone required")
    return result.astimezone(timezone.utc)


def number(value):
    if type(value) not in (int, float) or not isfinite(value):
        raise ValueError("Finite numeric evidence required")
    return float(value)


class MacroAnalyst:
    """Consumes economic vintage/order-flow evidence; never invents missing data."""
    def evaluate(self, state, *, symbol, snapshot_id, as_of=None):
        info = {**CONTRACTS["macro_analyst"], "status": "DATA_UNAVAILABLE", "regime": None}
        opinion = AgentOpinion("macro_analyst", "HOLD", 0, ("MACRO_DATA_UNAVAILABLE",), snapshot_id)
        if not state:
            return opinion, info
        now = timestamp(as_of) if as_of else datetime.now(timezone.utc)
        if (not isinstance(state, Mapping) or state.get("source") != "observed"
                or state.get("symbol") != symbol or state.get("snapshot_id") != snapshot_id
                or timestamp(state.get("available_at")) > now):
            raise ValueError("Macro evidence must match the symbol/snapshot and be known as of the decision")
        features = state.get("features")
        if not isinstance(features, Mapping) or set(features) != set(info["features"]):
            raise ValueError("Incomplete structural regime features")
        for value in features.values():
            number(value)
        if not -1 <= features["order_flow_imbalance"] <= 1:
            raise ValueError("Order-flow imbalance must be -1..1")
        regime = str(state.get("regime", "")).strip()
        if not regime or len(regime) > 50:
            raise ValueError("Macro regime is required")
        # Asset-specific directional interpretation is supplied explicitly.
        # A global regime name alone is never converted to a buy/sell signal.
        decision = {"BULLISH": "BUY", "BEARISH": "SELL", "NEUTRAL": "HOLD"}.get(state.get("market_bias"))
        if decision is None:
            raise ValueError("Invalid asset-specific macro bias")
        confidence = number(state.get("confidence"))
        if not 0 <= confidence <= 1:
            raise ValueError("Macro confidence must be 0..1")
        info.update(status="OBSERVED_CONTEXT", regime=regime, available_at=state["available_at"], features=dict(features))
        return AgentOpinion("macro_analyst", decision, confidence, ("regime=" + regime,), snapshot_id), info


class QuantitativeStrategist:
    """Technical/price-action/pair research is one vote, not duplicate votes."""
    def evaluate(self, signal, quality, *, snapshot_id):
        direction = str(signal.get("direction", "WAIT")).upper()
        decision = {"LONG": "BUY", "SHORT": "SELL"}.get(direction, "HOLD")
        confidence = number(signal.get("confidence", 0))
        confidence = confidence / 100 if confidence > 1 else confidence
        if not 0 <= confidence <= 1:
            raise ValueError("Quant confidence must be 0..1 or 0..100")
        if quality:
            execution = number(quality.get("execution_confidence", 0))
            execution = execution / 100 if execution > 1 else execution
            if not 0 <= execution <= 1:
                raise ValueError("Invalid execution confidence")
            confidence = min(confidence, execution)
            if execution < .35:
                decision = "HOLD"
        strategy = str(signal.get("strategy", "TECHNICAL"))
        status = "TECHNICAL_CONTEXT"
        if strategy.upper().startswith("STAT_ARB"):
            pair = signal.get("pair_validation")
            if (not isinstance(pair, Mapping) or pair.get("snapshot_id") != snapshot_id
                    or pair.get("out_of_sample_validated") is not True or pair.get("costs_included") is not True):
                decision, confidence, status = "HOLD", 0, "PAIR_VALIDATION_REQUIRED"
            else:
                status = "VALIDATED_PAIR_CONTEXT"
        reasons = signal.get("reasons") or ()
        evidence = tuple(str(x) for x in reasons[:8]) if isinstance(reasons, (list, tuple)) else ()
        return AgentOpinion("quantitative_strategist", decision, confidence, evidence, snapshot_id), {
            **CONTRACTS["quantitative_strategist"], "status": status, "strategy": strategy,
        }


class RiskExecutive:
    """Risk policy cannot be calibrated away or overridden by council weights."""
    def assess(self, risk, *, symbol, snapshot_id, open_symbols=(), correlation=None, as_of=None, position=None):
        checks = dict(position_sizing=False, correlation_limits=False, stop_losses=False)
        reasons = []
        if risk.get("approved") is not True:
            reasons.append("RISK_POLICY_REJECTED")
        try:
            entry, stop, target = (number(risk.get(k)) for k in ("entry", "stop_loss", "take_profit"))
            side = risk.get("direction")
            checks["stop_losses"] = (0 < stop < entry < target if side == "LONG" else
                                      0 < target < entry < stop if side == "SHORT" else False)
            size, actual, maximum = (number(risk.get(k)) for k in ("position_size", "actual_risk_amount", "maximum_risk_amount"))
            derived = size * abs(entry - stop)
            checks["position_sizing"] = (min(size, actual, maximum) > 0 and isfinite(derived)
                and max(actual, derived) <= maximum + .02 and isclose(actual, derived, abs_tol=.02, rel_tol=1e-6))
            if "max_position_value" in risk:
                cap = number(risk["max_position_value"])
                checks["position_sizing"] &= cap > 0 and size * entry <= cap + .02
        except (ValueError, TypeError):
            pass
        margin = None
        if position is not None:
            from app.risk.multi_asset import margin_health
            checks['margin_health'] = False
            try:
                health = position['margin_health']
                margin = margin_health(equity=health['equity'],used_margin=health['used_margin'],
                    required_margin=position['required_margin'],free_margin=health['free_margin'],
                    opening_cost=number(position['estimated_spread_cost']))
                checks['margin_health'] = margin['allowed']
                matches = (position.get('status') == 'APPROVED' and position.get('symbol') == symbol
                    and position.get('mode') == 'BROKER_ESTIMATE'
                    and position.get('direction') == {'LONG':'BUY','SHORT':'SELL'}.get(risk.get('direction'))
                    and isclose(number(position['entry_price']),number(risk['entry']),abs_tol=1e-8,rel_tol=0)
                    and isclose(number(position['sl_price']),number(risk['stop_loss']),abs_tol=1e-8,rel_tol=0)
                    and isclose(number(health['equity']),number(risk['account_balance']),abs_tol=.01,rel_tol=0)
                    and number(position['lots']) > 0
                    and 0 < number(position['estimated_total_risk']) <= number(position['risk_budget']) + 1e-8
                    and number(position['risk_budget']) <= number(risk['actual_risk_amount']) + 1e-8)
                checks['position_sizing'] &= matches
                reasons.extend(margin['reason_codes'])
            except (ValueError, TypeError, KeyError, AttributeError):
                checks['position_sizing'] = False
                reasons.append('MARGIN_DATA_UNAVAILABLE')
            if not checks['margin_health']:
                reasons.append('MARGIN_HEALTH_VETO')
        if not checks["position_sizing"]:
            reasons.append("POSITION_SIZING_VETO")
        if not checks["stop_losses"]:
            reasons.append("STOP_LOSS_VETO")
        symbols = set(open_symbols)
        if not symbols:
            checks["correlation_limits"] = True
        else:
            try:
                if not isinstance(correlation, Mapping) or correlation.get("symbol") != symbol or correlation.get("snapshot_id") != snapshot_id:
                    raise ValueError()
                now = timestamp(as_of) if as_of else datetime.now(timezone.utc)
                available = timestamp(correlation.get("available_at"))
                closed = timestamp(correlation.get("last_bar_closed_at"))
                interval = correlation.get("bar_seconds")
                count = correlation.get("sample_count")
                if (correlation.get("source") != "completed_bars"
                        or correlation.get("method") != "pearson_log_returns"
                        or type(interval) is not int or not 1 <= interval <= 86400
                        or type(count) is not int or count < 30
                        or not 0 <= (now - available).total_seconds() <= 2 * interval
                        or not 0 <= (available - closed).total_seconds() <= 2 * interval):
                    raise ValueError()
                limit = number(correlation.get("limit"))
                coefficients = correlation.get("coefficients")
                if not 0 < limit <= 1 or not isinstance(coefficients, Mapping) or not symbols.issubset(coefficients):
                    raise ValueError()
                values = [number(coefficients[key]) for key in symbols]
                if any(abs(value) > 1 for value in values):
                    raise ValueError()
                checks["correlation_limits"] = all(abs(value) < limit for value in values)
                if not checks["correlation_limits"]:
                    reasons.append("CORRELATION_LIMIT_EXCEEDED")
            except (ValueError, TypeError):
                reasons.append("CORRELATION_DATA_UNAVAILABLE")
        verdict = {"agent": "risk_executive", "authority": "ABSOLUTE_VETO", "executes_orders": False,
                "symbol": symbol, "snapshot_id": snapshot_id, "checks": checks,
                "allowed": risk.get("approved") is True and all(checks.values()), "reason_codes": reasons,
                "approved_cash_risk": risk.get("actual_risk_amount") if checks["position_sizing"] else None,
                "approved_stop_loss": risk.get("stop_loss") if checks["stop_losses"] else None}
        if position is not None:
            verdict.update(margin_health=margin,approved_lots=position.get('lots') if checks['position_sizing'] else None)
        return verdict


def verdict_allows(verdict, *, symbol, snapshot_id):
    try:
        if number(verdict.get("approved_cash_risk")) <= 0 or number(verdict.get("approved_stop_loss")) <= 0:
            return False
        if 'approved_lots' in verdict and (number(verdict['approved_lots']) <= 0
                or verdict.get('checks',{}).get('margin_health') is not True):
            return False
    except (ValueError, TypeError, AttributeError):
        return False
    return (isinstance(symbol, str) and bool(symbol) and isinstance(snapshot_id, str) and bool(snapshot_id)
            and isinstance(verdict, Mapping) and verdict.get("agent") == "risk_executive"
            and verdict.get("authority") == "ABSOLUTE_VETO" and verdict.get("allowed") is True
            and verdict.get("executes_orders") is False and verdict.get("symbol") == symbol
            and verdict.get("snapshot_id") == snapshot_id and isinstance(verdict.get("checks"), Mapping)
            and all(verdict["checks"].get(key) is True for key in CONTRACTS["risk_executive"]["checks"]))
