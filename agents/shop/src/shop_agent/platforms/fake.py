"""In-memory fake shop platform for offline testing and dry runs."""

from typing import Any

from revenue_swarm.enums import ListingStatus
from revenue_swarm.models.product import Product
from revenue_swarm.models.product_listing import ProductListing

from shop_agent.listing import handle_for
from shop_agent.platforms.base import ListingResult


class FakeShopPlatform:
    name = "fake"

    def __init__(self) -> None:
        self.products: dict[str, dict[str, Any]] = {}
        self.fulfilled: list[dict[str, Any]] = []

    def upsert_listing(
        self, product: Product, status: ListingStatus
    ) -> ListingResult:
        handle = handle_for(product)
        current = self.products.get(handle, {})
        gid = current.get("id") or f"gid://shopify/Product/{handle}"
        variant = (
            current.get("variant") or f"gid://shopify/ProductVariant/{handle}"
        )
        self.products[handle] = {
            "id": gid,
            "variant": variant,
            "status": status.value,
            "requiresShipping": False,
            "tracked": False,
        }
        return ListingResult(gid, variant, handle)

    def activate(self, listing: ProductListing) -> None:
        row = self.products.setdefault(
            listing.handle,
            {
                "id": listing.external_id
                or f"gid://shopify/Product/{listing.handle}",
                "variant": listing.external_variant_id
                or f"gid://shopify/ProductVariant/{listing.handle}",
                "requiresShipping": False,
                "tracked": False,
            },
        )
        row["status"] = ListingStatus.ACTIVE.value
        row["published"] = True

    def mark_fulfilled(self, order_gid: str) -> None:
        self.fulfilled.append({"id": order_gid, "notifyCustomer": False})
