"""Shop platform factory."""

from revenue_swarm import config

from shop_agent.platforms.base import ListingResult, ShopPlatform
from shop_agent.platforms.fake import FakeShopPlatform
from shop_agent.platforms.shopify import ShopifyPlatform

_FAKE = FakeShopPlatform()


def platform() -> ShopPlatform:
    if config.SHOP_PLATFORM == "shopify":
        return ShopifyPlatform()
    return _FAKE


__all__ = [
    "FakeShopPlatform",
    "ListingResult",
    "ShopPlatform",
    "ShopifyPlatform",
    "platform",
]
