from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    side: str
    volume: float
    order_type: str = "MARKET"
    stop_loss: float | None = None
    take_profit: float | None = None
    comment: str = "trading-ai"


class ExecutionAdapter(ABC):
    """Common execution contract for paper and broker adapters."""

    @abstractmethod
    def connect(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def account(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def positions(self, symbol: str | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def submit(self, order: OrderRequest) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError
