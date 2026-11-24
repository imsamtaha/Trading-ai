"""Deterministic ATLAS decision-matrix and risk-gating engine.

This module is independent of the LLM layer. It converts normalized analytical
evidence into reproducible long/short scores, conviction, risk score, and a
final trade/no-trade decision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


COMPONENT_WEIGHTS: dict[str, int] = {
    "structure": 20,
    "trend_mtf": 15,
    "support_resistance": 10,
    "liquidity": 10,
    "momentum": 10,
    "volume": 10,
    "volatility": 10,
    "price_action": 5,
    "macro": 10,
}

EXECUTION_TIMEFRAMES = ("5m", "15m", "30m", "1h")
STRUCTURAL_TIMEFRAMES = ("4h", "1d", "1w")


class Regime(str, Enum):
    TRENDING_BULL = "trending_bull"
    TRENDING_BEAR = "trending_bear"
    RANGE_BOUND = "range_bound"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    UNKNOWN = "unknown"


class Bias(str, Enum):
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


class Conviction(str, Enum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


class DecisionStatus(str, Enum):
    VALID = "valid"
    NO_TRADE = "no_trade"


@dataclass(frozen=True)
class RiskFlags:
    data_stale: bool = False
    critical_data_missing: bool = False
    invalidation_undefined: bool = False
    extreme_volatility: bool = False
    major_event_imminent: bool = False
    chasing_entry: bool = False
    higher_timeframe_conflict: bool = False
    excessive_account_risk: bool = False


@dataclass(frozen=True)
class ScoringInput:
    """Normalized evidence; every factor must be in [-1, 1]."""

    asset: str
    timeframe: str
    regime: Regime
    factors: Mapping[str, float]
    risk_score: float = 0.0
    risk_reward: float | None = None
    account_risk_fraction: float = 0.01
    risk_flags: RiskFlags = field(default_factory=RiskFlags)


@dataclass(frozen=True)
class ScoreBreakdown:
    long: dict[str, float]
    short: dict[str, float]
    long_score: float
    short_score: float
    directional_edge: float
    confluence_count_long: int
    confluence_count_short: int
    confluence_factors_long: tuple[str, ...]
    confluence_factors_short: tuple[str, ...]


@dataclass(frozen=True)
class AtlasDecision:
    asset: str
    timeframe: str
    regime: str
    bias: Bias
    conviction: Conviction | None
    status: DecisionStatus
    long_score: float
    short_score: float
    directional_edge: float
    risk_score: float
    risk_reward: float | None
    confluence_count: int
    confluence_factors: tuple[str, ...]
    veto_reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "asset": self.asset,
            "timeframe": self.timeframe,
            "regime": self.regime,
            "bias": self.bias.value,
            "conviction": self.conviction.value if self.conviction else None,
            "status": self.status.value,
            "long_score": round(self.long_score, 2),
            "short_score": round(self.short_score, 2),
            "directional_edge": round(self.directional_edge, 2),
            "risk_score": round(self.risk_score, 2),
            "risk_reward": round(self.risk_reward, 2) if self.risk_reward is not None else None,
            "confluence": {
                "count": self.confluence_count,
                "factors": list(self.confluence_factors),
            },
            "veto_reasons": list(self.veto_reasons),
        }


class AtlasScoringEngine:
    """ATLAS v1 deterministic scorer with hard risk vetoes."""

    MIN_DIRECTIONAL_EDGE = 15.0
    MIN_RR = 1.5
    HIGH_SCORE = 75.0
    MODERATE_SCORE = 60.0
    HIGH_EDGE = 25.0
    MODERATE_EDGE = 15.0
    HIGH_CONFLUENCE = 3
    MODERATE_CONFLUENCE = 2
    MAX_ACCOUNT_RISK = 0.02

    def score(self, data: ScoringInput) -> AtlasDecision:
        self._validate(data)
        breakdown = self._score_components(data.factors)
        veto_reasons = self._risk_vetoes(data)
        bias = self._determine_bias(
            breakdown.long_score,
            breakdown.short_score,
            data.regime,
            veto_reasons,
        )

        if bias is Bias.LONG:
            conviction = self._conviction(
                breakdown.long_score,
                breakdown.directional_edge,
                breakdown.confluence_count_long,
            )
            factors = breakdown.confluence_factors_long
            count = breakdown.confluence_count_long
        elif bias is Bias.SHORT:
            conviction = self._conviction(
                breakdown.short_score,
                breakdown.directional_edge,
                breakdown.confluence_count_short,
            )
            factors = breakdown.confluence_factors_short
            count = breakdown.confluence_count_short
        else:
            conviction = None
            factors = ()
            count = 0

        status = DecisionStatus.VALID if bias is not Bias.NEUTRAL else DecisionStatus.NO_TRADE
        if veto_reasons:
            status = DecisionStatus.NO_TRADE
            conviction = None

        return AtlasDecision(
            asset=data.asset,
            timeframe=data.timeframe,
            regime=data.regime.value,
            bias=bias,
            conviction=conviction,
            status=status,
            long_score=breakdown.long_score,
            short_score=breakdown.short_score,
            directional_edge=breakdown.directional_edge,
            risk_score=max(0.0, min(100.0, data.risk_score)),
            risk_reward=data.risk_reward,
            confluence_count=count,
            confluence_factors=factors,
            veto_reasons=veto_reasons,
        )

    def _validate(self, data: ScoringInput) -> None:
        if not data.asset.strip():
            raise ValueError("asset is required")
        if not data.timeframe.strip():
            raise ValueError("timeframe is required")
        if not 0 <= data.risk_score <= 100:
            raise ValueError("risk_score must be between 0 and 100")
        if not 0 <= data.account_risk_fraction <= 1:
            raise ValueError("account_risk_fraction must be between 0 and 1")
        if data.risk_reward is not None and data.risk_reward < 0:
            raise ValueError("risk_reward cannot be negative")
        for name, value in data.factors.items():
            if name not in COMPONENT_WEIGHTS:
                raise ValueError(f"unsupported scoring component: {name}")
            if not -1 <= float(value) <= 1:
                raise ValueError(f"factor '{name}' must be between -1 and 1")

    @staticmethod
    def _score_components(factors: Mapping[str, float]) -> ScoreBreakdown:
        long: dict[str, float] = {}
        short: dict[str, float] = {}
        for name, weight in COMPONENT_WEIGHTS.items():
            signal = max(-1.0, min(1.0, float(factors.get(name, 0.0))))
            long[name] = max(signal, 0.0) * weight
            short[name] = max(-signal, 0.0) * weight

        long_score = sum(long.values())
        short_score = sum(short.values())
        edge = long_score - short_score
        long_factors = tuple(name for name, value in long.items() if value > 0)
        short_factors = tuple(name for name, value in short.items() if value > 0)

        return ScoreBreakdown(
            long=long,
            short=short,
            long_score=long_score,
            short_score=short_score,
            directional_edge=edge,
            confluence_count_long=len(long_factors),
            confluence_count_short=len(short_factors),
            confluence_factors_long=long_factors,
            confluence_factors_short=short_factors,
        )

    def _risk_vetoes(self, data: ScoringInput) -> tuple[str, ...]:
        flags = data.risk_flags
        reasons: list[str] = []
        mapping = (
            (flags.data_stale, "market_data_stale"),
            (flags.critical_data_missing, "critical_data_missing"),
            (flags.invalidation_undefined, "invalidation_undefined"),
            (flags.extreme_volatility, "extreme_volatility"),
            (flags.major_event_imminent, "major_event_imminent"),
            (flags.chasing_entry, "entry_requires_chasing"),
            (flags.higher_timeframe_conflict, "higher_timeframe_conflict"),
            (flags.excessive_account_risk, "excessive_account_risk"),
        )
        reasons.extend(reason for enabled, reason in mapping if enabled)
        if data.account_risk_fraction > self.MAX_ACCOUNT_RISK:
            reasons.append("account_risk_above_2_percent")
        if data.risk_reward is None:
            reasons.append("risk_reward_undefined")
        elif data.risk_reward < self.MIN_RR:
            reasons.append("risk_reward_below_1_5")
        return tuple(reasons)

    def _determine_bias(
        self,
        long_score: float,
        short_score: float,
        regime: Regime,
        veto_reasons: tuple[str, ...],
    ) -> Bias:
        if veto_reasons:
            return Bias.NEUTRAL
        edge = long_score - short_score
        if abs(edge) < self.MIN_DIRECTIONAL_EDGE:
            return Bias.NEUTRAL
        if edge > 0:
            if regime is Regime.TRENDING_BEAR and long_score < self.HIGH_SCORE:
                return Bias.NEUTRAL
            return Bias.LONG
        if regime is Regime.TRENDING_BULL and short_score < self.HIGH_SCORE:
            return Bias.NEUTRAL
        return Bias.SHORT

    def _conviction(self, score: float, edge: float, confluence: int) -> Conviction:
        if score >= self.HIGH_SCORE and edge >= self.HIGH_EDGE and confluence >= self.HIGH_CONFLUENCE:
            return Conviction.HIGH
        if score >= self.MODERATE_SCORE and edge >= self.MODERATE_EDGE and confluence >= self.MODERATE_CONFLUENCE:
            return Conviction.MODERATE
        return Conviction.LOW


def calculate_position_size(
    account_equity: float,
    entry_price: float,
    stop_price: float,
    risk_fraction: float = 0.01,
    contract_multiplier: float = 1.0,
) -> float:
    """Size from account risk divided by invalidation distance.

    Leverage is intentionally excluded: it must not be used to justify larger
    account risk. Margin and liquidation controls belong to the risk/execution
    layer.
    """
    if account_equity <= 0:
        raise ValueError("account_equity must be positive")
    if entry_price <= 0 or stop_price <= 0:
        raise ValueError("entry_price and stop_price must be positive")
    if not 0 < risk_fraction <= 0.02:
        raise ValueError("risk_fraction must be greater than 0 and at most 2%")
    if contract_multiplier <= 0:
        raise ValueError("contract_multiplier must be positive")

    distance = abs(entry_price - stop_price)
    if distance == 0:
        raise ValueError("entry_price and stop_price cannot be equal")

    risk_amount = account_equity * risk_fraction
    return risk_amount / (distance * contract_multiplier)
