"""Multi-asset sizing estimates and the deterministic 20% / 200% margin veto."""
from copy import deepcopy
from decimal import Decimal, ROUND_FLOOR
from math import isfinite
from numbers import Real

MAX_FREE_MARGIN_FRACTION = .20
MIN_MARGIN_LEVEL_PCT = 200.0

# User-supplied USD simulation assumptions, never broker specifications.
PAPER_ASSET_SPECS = {
    'XAUUSD': dict(contract_size=100, leverage=100, min_lot=.01, lot_step=.01, spread=.30),
    'EURUSD': dict(contract_size=100000, leverage=200, min_lot=.01, lot_step=.01, spread=.00015),
    'BTCUSD': dict(contract_size=1, leverage=10, min_lot=.01, lot_step=.01, spread=15.0),
    'SPX500': dict(contract_size=1, leverage=20, min_lot=.1, lot_step=.1, spread=.50),
}


def finite(value, name, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
        raise ValueError(name + ' must be finite numeric evidence')
    value = float(value)
    if value < 0 or (positive and value == 0):
        raise ValueError(name + ' must be ' + ('positive' if positive else 'nonnegative'))
    return value


def margin_health(*, equity, used_margin, required_margin, free_margin=None, opening_cost=0):
    equity = finite(equity, 'Equity', positive=True)
    used = finite(used_margin, 'Used margin')
    required = finite(required_margin, 'Required margin')
    cost = finite(opening_cost, 'Estimated opening cost')
    calculated = max(0.0, equity - used)
    reported = calculated if free_margin is None else finite(free_margin, 'Free margin')
    effective = min(calculated, reported)
    maximum = effective * MAX_FREE_MARGIN_FRACTION
    projected_used = used + required
    if not isfinite(projected_used):
        raise ValueError('Projected used margin is nonfinite')
    current_level = equity / used * 100 if used else None
    projected_equity = equity - cost
    projected_level = projected_equity / projected_used * 100 if projected_used else None
    # No Infinity is serialized for an account with zero used margin.
    if any(value is not None and not isfinite(value) for value in (current_level, projected_level)):
        raise ValueError('Margin level is nonfinite')
    reasons = []
    if effective <= 0:
        reasons.append('NO_FREE_MARGIN')
    if projected_equity <= 0:
        reasons.append('PROJECTED_EQUITY_NONPOSITIVE')
    if required > maximum:
        reasons.append('MARGIN_USAGE_EXCEEDED')
    if ((current_level is not None and current_level < MIN_MARGIN_LEVEL_PCT)
            or (projected_level is not None and projected_level < MIN_MARGIN_LEVEL_PCT)):
        reasons.append('MARGIN_LEVEL_TOO_LOW')
    return dict(allowed=not reasons, reason_codes=reasons, equity=equity, used_margin=used,
        free_margin=reported, effective_free_margin=effective, required_margin=required,
        maximum_required_margin=maximum, projected_used_margin=projected_used,
        opening_cost=cost, projected_equity=projected_equity,
        current_margin_level_pct=current_level, projected_margin_level_pct=projected_level,
        max_free_margin_fraction=MAX_FREE_MARGIN_FRACTION, min_margin_level_pct=MIN_MARGIN_LEVEL_PCT)


class MultiAssetRiskEngine:
    """A position estimate, never an order sender or full portfolio approval."""
    def __init__(self, account_equity, max_account_risk_pct=.01, *, broker=None):
        self.equity = finite(account_equity, 'Equity', positive=True)
        self.max_risk_pct = finite(max_account_risk_pct, 'Risk fraction', positive=True)
        if self.max_risk_pct > .02:
            raise ValueError('Risk fraction exceeds the existing 2% per-trade ceiling')
        self.broker = broker
        self.asset_specs = deepcopy(PAPER_ASSET_SPECS)

    @staticmethod
    def _rejected(reason, **details):
        return dict(status='REJECTED_BY_RISK_EXECUTIVE', approved=False,
                    reason=reason, reason_codes=[reason], broker_execution_allowed=False, **details)

    def calculate_position(self, symbol, entry_price, sl_price, free_margin, *,
            used_margin=None, direction=None, max_cash_risk=None,
            entry_includes_spread=False, spread_price=None):
        if self.broker is None and symbol not in self.asset_specs:
            raise ValueError(f'Asset {symbol} not supported in ATLAS paper specs')
        try:
            entry = finite(entry_price, 'Entry', positive=True)
            stop = finite(sl_price, 'Stop loss', positive=True)
            free = finite(free_margin, 'Free margin')
            side = {'LONG':'BUY','SHORT':'SELL'}.get(direction, direction)
            side = side or ('BUY' if stop < entry else 'SELL')
            if side not in {'BUY','SELL'} or not (stop < entry if side == 'BUY' else stop > entry):
                raise ValueError('Invalid directional stop loss')
            if type(entry_includes_spread) is not bool:
                raise ValueError('Spread inclusion must be explicit boolean evidence')
            budget = self.equity * self.max_risk_pct
            if max_cash_risk is not None:
                budget = min(budget, finite(max_cash_risk, 'Approved cash risk', positive=True))
            budget = finite(budget, 'Risk budget', positive=True)
            if self.broker is None:
                spec = self.asset_specs[symbol]
                contract = finite(spec['contract_size'], 'Contract size', positive=True)
                minimum = finite(spec['min_lot'], 'Minimum lot', positive=True)
                step = finite(spec['lot_step'], 'Lot step', positive=True)
                leverage = finite(spec['leverage'], 'Leverage', positive=True)
                maximum = None
                spread = finite(spec['spread'] if spread_price is None else spread_price, 'Spread')
                used = self.equity - free if used_margin is None else used_margin
                reference = minimum
                per_lot_risk = contract * (abs(entry - stop) + (0 if entry_includes_spread else spread))
                reference_risk = reference * per_lot_risk
                mode = 'PAPER_ESTIMATE'
            else:
                if used_margin is None or entry_includes_spread is not True or spread_price is None:
                    raise ValueError('Broker sizing requires used margin and executable-price/spread evidence')
                info = self.broker.symbol_info(symbol)
                contract = finite(info.trade_contract_size, 'Broker contract size', positive=True)
                minimum = finite(info.volume_min, 'Broker minimum', positive=True)
                step = finite(info.volume_step, 'Broker step', positive=True)
                maximum = finite(info.volume_max, 'Broker maximum', positive=True)
                if maximum < minimum:
                    raise ValueError('Invalid broker volume bounds')
                used = used_margin
                spread = finite(spread_price, 'Actual spread')
                if abs(entry - stop) <= spread:
                    return self._rejected('STOP_INSIDE_SPREAD', symbol=symbol)
                reference = minimum
                reference_risk = self.broker.cash_risk(symbol, entry, stop, reference)
                mode = 'BROKER_ESTIMATE'
            finite(used, 'Used margin')
            reference_risk = finite(reference_risk, 'Reference stop risk', positive=True)
            raw = Decimal(str(budget)) * Decimal(str(reference)) / Decimal(str(reference_risk))
            if maximum is not None:
                raw = min(raw, Decimal(str(maximum)))
            increment = Decimal(str(step))
            lots = float((raw / increment).to_integral_value(rounding=ROUND_FLOOR) * increment)
            if lots < minimum:
                return self._rejected('MINIMUM_LOT_EXCEEDS_RISK', symbol=symbol, risk_budget=budget)
            units = finite(lots * contract, 'Units', positive=True)
            notional = finite(units * entry, 'Quote-currency notional', positive=True)
            if self.broker is None:
                stop_risk = units * abs(entry - stop)
                spread_cost = units * spread
                total = stop_risk + (0 if entry_includes_spread else spread_cost)
                required = notional / leverage
            else:
                stop_risk = self.broker.cash_risk(symbol, entry, stop, lots)
                spread_stop = entry - spread if side == 'BUY' else entry + spread
                spread_cost = self.broker.cash_risk(symbol, entry, spread_stop, lots) if spread else 0
                # The executable ask/bid-to-stop distance already contains spread.
                total = stop_risk
                required = self.broker.required_margin(symbol, side, lots, entry)
            total = finite(total, 'Estimated total stop risk', positive=True)
            spread_cost = finite(spread_cost, 'Estimated spread cost')
            if total > budget + 1e-8:
                return self._rejected('CASH_RISK_EXCEEDED', symbol=symbol, risk_budget=budget)
            health = margin_health(equity=self.equity, used_margin=used, required_margin=required,
                                   free_margin=free,opening_cost=spread_cost)
            return dict(status='APPROVED' if health['allowed'] else 'REJECTED_BY_RISK_EXECUTIVE',
                approved=health['allowed'], reason='Sizing estimate acceptable' if health['allowed'] else ', '.join(health['reason_codes']),
                reason_codes=health['reason_codes'], symbol=symbol, direction=side, mode=mode,
                lots=lots, units=units, entry_price=entry, sl_price=stop, equity=self.equity,
                notional_value=notional, notional_currency='SYMBOL_QUOTE_CURRENCY',
                risk_budget=budget, estimated_stop_risk=stop_risk, estimated_spread_cost=spread_cost,
                estimated_total_risk=total, spread_included_in_stop_risk=entry_includes_spread,
                required_margin=required, margin_health=health, broker_execution_allowed=False)
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError, OverflowError) as exc:
            return self._rejected('SIZING_DATA_UNAVAILABLE', symbol=symbol, detail=str(exc))
