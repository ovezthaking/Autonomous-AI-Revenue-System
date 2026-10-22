from revenue_swarm import config
from revenue_swarm.networks.awin import AwinNetwork
from revenue_swarm.networks.base import (
    AffiliateNetwork,
    PerformanceRow,
    PermanentNetworkError,
    TrackingLink,
)
from revenue_swarm.networks.cj import CjNetwork
from revenue_swarm.networks.impact import ImpactNetwork
from revenue_swarm.networks.simple import AmazonNetwork, ManualNetwork

KNOWN_NETWORKS = ("manual", "awin", "impact", "cj", "amazon")


def network_for(name: str | None) -> AffiliateNetwork:
    key = (name or "manual").strip().lower()
    if key == "awin":
        return AwinNetwork()
    if key == "impact":
        return ImpactNetwork()
    if key == "cj":
        return CjNetwork()
    if key == "amazon":
        return AmazonNetwork()
    return ManualNetwork()


def active_networks() -> list[AffiliateNetwork]:
    names = [
        item.strip().lower()
        for item in config.AFFILIATE_NETWORKS.split(",")
        if item.strip()
    ]
    return [network_for(name) for name in names]


__all__ = [
    "KNOWN_NETWORKS",
    "AffiliateNetwork",
    "AmazonNetwork",
    "AwinNetwork",
    "CjNetwork",
    "ImpactNetwork",
    "ManualNetwork",
    "PerformanceRow",
    "PermanentNetworkError",
    "TrackingLink",
    "active_networks",
    "network_for",
]
