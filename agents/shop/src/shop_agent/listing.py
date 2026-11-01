from __future__ import annotations

import html
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from revenue_swarm import config
from revenue_swarm.enums import ListingStatus
from revenue_swarm.models.product import Product
from revenue_swarm.models.product_listing import ProductListing
from sqlalchemy import select
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from shop_agent.platforms.base import ListingResult


def handle_for(product: Product) -> str:
    return f"rs-{product.id.hex[:12]}"


def clamp_price(cents: int) -> int:
    return min(
        max(cents, config.SHOP_PRICE_MIN_CENTS), config.SHOP_PRICE_MAX_CENTS
    )


def format_price(cents: int) -> str:
    return f"{cents // 100}.{cents % 100:02d}"


def render_description(product: Product) -> str:
    text = html.escape(product.description or product.title)
    return (
        f"<p>{text}</p>"
        "<p>This file was drafted with AI and reviewed by a person "
        "before it went on sale.</p>"
    )


def save_listing(
    db: Session,
    product: Product,
    result: ListingResult,
    *,
    platform_name: str = "shopify",
    status: ListingStatus = ListingStatus.DRAFT,
) -> ProductListing:
    row = db.scalar(
        select(ProductListing).where(
            ProductListing.product_id == product.id,
            ProductListing.platform == platform_name,
        )
    )
    if row is None:
        row = ProductListing(
            product_id=product.id,
            platform=platform_name,
            handle=result.handle,
            status=status.value,
        )
        db.add(row)
    row.external_id = result.external_id
    row.external_variant_id = result.external_variant_id
    row.last_synced_at = datetime.now(UTC)
    row.error = None
    db.commit()
    db.refresh(row)
    return row
