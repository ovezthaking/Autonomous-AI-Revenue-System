from revenue_swarm.networks.awin import AwinNetwork
from revenue_swarm.networks.base import (
    AffiliateNetwork,
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


__all__ = [
    "KNOWN_NETWORKS",
    "AffiliateNetwork",
    "AmazonNetwork",
    "AwinNetwork",
    "CjNetwork",
    "ImpactNetwork",
    "ManualNetwork",
    "PermanentNetworkError",
    "TrackingLink",
    "network_for",
]
