"""ShopPlatform protocol and ListingResult data structure."""

from dataclasses import dataclass
from typing import Protocol

from revenue_swarm.enums import ListingStatus
from revenue_swarm.models.product import Product
from revenue_swarm.models.product_listing import ProductListing


@dataclass(frozen=True)
class ListingResult:
    external_id: str
    external_variant_id: str | None
    handle: str


class ShopPlatform(Protocol):
    name: str

    def upsert_listing(
        self, product: Product, status: ListingStatus
    ) -> ListingResult: ...

    def activate(self, listing: ProductListing) -> None: ...

    def mark_fulfilled(self, order_gid: str) -> None: ...
