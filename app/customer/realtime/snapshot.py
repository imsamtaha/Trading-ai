from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4
from types import MappingProxyType

from app.customer.contracts import CustomerContext, MarketSnapshot


def _as_utc(value: datetime | str) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def build_snapshot(
    *,
    context: CustomerContext,
    symbol: str,
    timeframe: str,
    market: dict,
    account: dict,
    system: dict,
    now: datetime | None = None,
    news: dict | None = None,
    sentiment: dict | None = None,
) -> MarketSnapshot:
    snapshot_time = _as_utc(now or datetime.now(timezone.utc))
    market_time_raw = market.get("timestamp")
    if market_time_raw is None:
        raise ValueError("market timestamp is required")
    market_time = _as_utc(market_time_raw)
    return MarketSnapshot(
        snapshot_id=str(uuid4()),
        customer_id=context.customer_id,
        account_id=context.account_id,
        mode=context.mode,
        symbol=symbol.upper(),
        timeframe=timeframe,
        market_timestamp=market_time,
        snapshot_timestamp=snapshot_time,
        market=MappingProxyType(dict(market)),
        account=MappingProxyType(dict(account)),
        system=MappingProxyType(dict(system)),
        news=MappingProxyType(dict(news)) if news is not None else None,
        sentiment=MappingProxyType(dict(sentiment)) if sentiment is not None else None,
    )


def snapshot_is_stale(snapshot: MarketSnapshot, *, max_age_seconds: float) -> bool:
    age = (snapshot.snapshot_timestamp - snapshot.market_timestamp).total_seconds()
    return age > max_age_seconds
