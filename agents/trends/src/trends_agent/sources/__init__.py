"""Signal source registry."""

from typing import Protocol

from revenue_swarm import config
from revenue_swarm.models.trend_signal import TrendSignal
from sqlalchemy.orm import Session

from trends_agent.sources.gsc import GscSource
from trends_agent.sources.orders import OrdersSource
from trends_agent.sources.own import OwnSource
from trends_agent.sources.search import SearchSource


class SignalSource(Protocol):
    name: str

    def collect(self, db: Session) -> list[TrendSignal]: ...


_REGISTRY: dict[str, SignalSource] = {
    "own": OwnSource(),
    "orders": OrdersSource(),
    "search": SearchSource(),
    "gsc": GscSource(),
}


def active_sources() -> list[SignalSource]:
    names = [
        part.strip().lower()
        for part in config.TRENDS_SOURCES.split(",")
        if part.strip()
    ]
    return [_REGISTRY[name] for name in names if name in _REGISTRY]


__all__ = [
    "GscSource",
    "OrdersSource",
    "OwnSource",
    "SearchSource",
    "SignalSource",
    "active_sources",
]
