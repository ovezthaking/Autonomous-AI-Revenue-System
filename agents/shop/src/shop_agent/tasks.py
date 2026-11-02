"""Celery tasks for shop-agent."""

import tempfile
import uuid
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from revenue_swarm import config, storage
from revenue_swarm.celery import celery_app
from revenue_swarm.config import (
    SHOP_ENABLED,
    SHOP_MAX_NEW_LISTINGS_PER_DAY,
)
from revenue_swarm.db import SessionLocal
from revenue_swarm.enums import (
    ListingStatus,
    OrderStatus,
    ProductKind,
    ProductStatus,
)
from revenue_swarm.fulfillment import fulfill_order
from revenue_swarm.models.download_grant import DownloadGrant
from revenue_swarm.models.order import Order
from revenue_swarm.models.payment_event import PaymentEvent
from revenue_swarm.models.product import Product
from revenue_swarm.models.product_idea import ProductIdea
from revenue_swarm.models.product_listing import ProductListing
from revenue_swarm.render.pdf import render_pdf, validate_pdf
from revenue_swarm.tasks import TaskName
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shop_agent.build import (
    BUILD_PROMPT,
    PrintableSpec,
    html_for,
    page_css,
    structured,
)
from shop_agent.listing import clamp_price, save_listing
from shop_agent.platforms import platform

MIN_PRINTABLE_PDF_BYTES = 1_000


def validate_assets(pdf_path: Path, page_count: int) -> None:
    validate_pdf(
        pdf_path, min_pages=page_count, min_bytes=MIN_PRINTABLE_PDF_BYTES
    )


def session_id(order_gid: str, line_gid: str) -> str:
    return f"{order_gid}:{line_gid}"


def _event(db: Session, webhook_id: str) -> PaymentEvent | None:
    return db.scalar(
        select(PaymentEvent).where(
            PaymentEvent.provider == "shopify",
            PaymentEvent.event_id == webhook_id,
        )
    )


def _listing_by_variant(
    db: Session, variant_gid: str
) -> ProductListing | None:
    if not variant_gid:
        return None
    return db.scalar(
        select(ProductListing).where(
            ProductListing.external_variant_id == variant_gid
        )
    )


def _variant_gid(line: dict[str, Any]) -> str:
    if line.get("admin_graphql_api_variant_id"):
        return str(line["admin_graphql_api_variant_id"])
    if line.get("variant_id"):
        return f"gid://shopify/ProductVariant/{line['variant_id']}"
    return ""


def _line_gid(line: dict[str, Any]) -> str:
    if line.get("admin_graphql_api_id"):
        return str(line["admin_graphql_api_id"])
    if line.get("id"):
        return f"gid://shopify/LineItem/{line['id']}"
    return ""


def _line_amount_cents(line: dict[str, Any], fallback_cents: int) -> int:
    raw_price = line.get("price")
    if raw_price is None:
        return fallback_cents
    try:
        price = Decimal(str(raw_price))
        qty = int(line.get("quantity", 1))
        discount = Decimal(str(line.get("total_discount", "0")))
        cents = int((price * qty - discount) * 100)
        return max(cents, 0)
    except (InvalidOperation, ValueError, TypeError):
        return fallback_cents


def _get_or_create_order(
    db: Session,
    provider: str,
    session_id: str,
    product_id: uuid.UUID,
    email: str | None,
    amount_cents: int | None = None,
    currency: str | None = None,
) -> Order:
    existing = db.scalar(
        select(Order).where(
            Order.provider == provider,
            Order.provider_session_id == session_id,
        )
    )
    if existing is not None:
        return existing
    product = db.get(Product, product_id)
    assert product is not None
    resolved_cents = (
        amount_cents if amount_cents is not None else product.price_cents
    )
    resolved_currency = currency or product.currency
    order = Order(
        product_id=product_id,
        provider=provider,
        provider_session_id=session_id,
        email=email,
        amount_cents=resolved_cents,
        currency=resolved_currency,
        status=OrderStatus.PAID.value,
    )
    try:
        with db.begin_nested():
            db.add(order)
            db.flush()
        db.commit()
        return order
    except IntegrityError:
        existing = db.scalar(
            select(Order).where(
                Order.provider == provider,
                Order.provider_session_id == session_id,
            )
        )
        assert existing is not None
        return existing


def _grants(db: Session, order_id: uuid.UUID) -> list[DownloadGrant]:
    return list(
        db.scalars(
            select(DownloadGrant).where(DownloadGrant.order_id == order_id)
        ).all()
    )


def _refund_order_gid(payload: dict[str, Any]) -> str:
    if payload.get("order_gid"):
        return str(payload["order_gid"])
    if payload.get("order_id"):
        raw = str(payload["order_id"])
        if raw.startswith("gid://shopify/Order/"):
            return raw
        return f"gid://shopify/Order/{raw}"
    admin_gid = str(payload.get("admin_graphql_api_id") or "")
    if admin_gid.startswith("gid://shopify/Order/"):
        return admin_gid
    return ""


def _refund_session_ids(order_gid: str, payload: dict[str, Any]) -> list[str]:
    items = payload.get("refund_line_items") or []
    sessions: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        nested = item.get("line_item") or {}
        line_gid = ""
        if isinstance(nested, dict) and nested.get("admin_graphql_api_id"):
            line_gid = str(nested["admin_graphql_api_id"])
        elif item.get("line_item_id"):
            raw_line = str(item["line_item_id"])
            line_gid = (
                raw_line
                if raw_line.startswith("gid://shopify/LineItem/")
                else f"gid://shopify/LineItem/{raw_line}"
            )
        if line_gid:
            sessions.append(session_id(order_gid, line_gid))
    return sessions


def _listed_today(db: Session) -> int:
    start = datetime.now(UTC).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return int(
        db.scalar(
            select(func.count())
            .select_from(ProductListing)
            .where(ProductListing.created_at >= start)
        )
        or 0
    )


@celery_app.task(name=TaskName.SHOP_FULFILL.value, soft_time_limit=120)
def shop_fulfill_task(webhook_id: str) -> dict[str, int]:
    db = SessionLocal()
    try:
        event = _event(db, webhook_id)
        if event is None:
            return {"delivered": 0}
        payload = event.payload or {}
        order_gid = str(
            payload.get("admin_graphql_api_id")
            or (
                f"gid://shopify/Order/{payload['id']}"
                if payload.get("id")
                else ""
            )
        )
        if not order_gid:
            return {"delivered": 0}
        delivered = 0
        for line in payload.get("line_items") or []:
            variant = _variant_gid(line)
            listing = _listing_by_variant(db, variant)
            if listing is None:
                continue
            product = db.get(Product, listing.product_id)
            fallback_cents = product.price_cents if product else 0
            order = _get_or_create_order(
                db,
                provider="shopify",
                session_id=session_id(order_gid, _line_gid(line)),
                product_id=listing.product_id,
                email=payload.get("email"),
                amount_cents=_line_amount_cents(line, fallback_cents),
                currency=payload.get("currency"),
            )
            delivered += fulfill_order(db, order)
        if delivered:
            platform().mark_fulfilled(order_gid)
        event.processed_at = datetime.now(UTC)
        db.commit()
        return {"delivered": delivered}
    finally:
        db.close()


@celery_app.task(name=TaskName.SHOP_REFUND.value)
def shop_refund_task(webhook_id: str) -> dict[str, int]:
    db = SessionLocal()
    try:
        event = _event(db, webhook_id)
        if event is None:
            return {"refunded": 0}
        payload = event.payload or {}
        order_gid = _refund_order_gid(payload)
        if not order_gid:
            return {"refunded": 0}
        target_sessions = _refund_session_ids(order_gid, payload)
        if target_sessions:
            rows = list(
                db.scalars(
                    select(Order)
                    .where(
                        Order.provider == "shopify",
                        Order.provider_session_id.in_(target_sessions),
                    )
                    .with_for_update()
                ).all()
            )
        else:
            prefix = f"{order_gid}:"
            rows = list(
                db.scalars(
                    select(Order)
                    .where(
                        Order.provider == "shopify",
                        Order.provider_session_id.startswith(prefix),
                    )
                    .with_for_update()
                ).all()
            )
        for order in rows:
            order.status = OrderStatus.REFUNDED.value
            for grant in _grants(db, order.id):
                grant.revoked = True
        event.processed_at = datetime.now(UTC)
        db.commit()
        return {"refunded": len(rows)}
    finally:
        db.close()


@celery_app.task(name=TaskName.SHOP_SYNC.value)
def sync_ebooks_task() -> dict[str, int]:
    if not (SHOP_ENABLED or config.SHOP_ENABLED):
        return {"listed": 0}
    db = SessionLocal()
    try:
        products = db.scalars(
            select(Product).where(
                Product.kind == ProductKind.EBOOK.value,
                Product.status == ProductStatus.LIVE.value,
            )
        ).all()
        listed = 0
        for product in products:
            existing = db.scalar(
                select(ProductListing).where(
                    ProductListing.product_id == product.id,
                    ProductListing.platform == "shopify",
                )
            )
            if existing is not None and existing.status in {
                ListingStatus.ACTIVE.value,
                ListingStatus.ARCHIVED.value,
            }:
                continue
            if (
                existing is None
                and _listed_today(db) >= SHOP_MAX_NEW_LISTINGS_PER_DAY
            ):
                break
            result = platform().upsert_listing(product, ListingStatus.DRAFT)
            save_listing(db, product, result)
            listed += 1
        return {"listed": listed}
    finally:
        db.close()


@celery_app.task(name=TaskName.SHOP_LIST.value)
def list_task(product_id: str) -> dict[str, str]:
    db = SessionLocal()
    try:
        product = db.get(Product, uuid.UUID(product_id))
        if product is None:
            return {"status": "not_found"}
        existing = db.scalar(
            select(ProductListing).where(
                ProductListing.product_id == product.id,
                ProductListing.platform == "shopify",
            )
        )
        if (
            existing is None
            and _listed_today(db) >= SHOP_MAX_NEW_LISTINGS_PER_DAY
        ):
            return {"status": "daily_limit_reached"}
        target_status = (
            ListingStatus.ACTIVE
            if existing and existing.status == ListingStatus.ACTIVE.value
            else ListingStatus.DRAFT
        )
        result = platform().upsert_listing(product, target_status)
        listing = save_listing(db, product, result, status=target_status)
        return {"status": listing.status, "listing_id": str(listing.id)}
    finally:
        db.close()


@celery_app.task(name=TaskName.SHOP_ACTIVATE.value)
def activate_task(listing_id: str) -> dict[str, str]:
    db = SessionLocal()
    try:
        listing = db.get(ProductListing, uuid.UUID(listing_id))
        if listing is None:
            return {"status": "not_found"}
        platform().activate(listing)
        listing.status = ListingStatus.ACTIVE.value
        product = db.get(Product, listing.product_id)
        if product is not None and product.status == ProductStatus.DRAFT.value:
            product.status = ProductStatus.LIVE.value
        db.commit()
        return {"status": listing.status}
    finally:
        db.close()


@celery_app.task(name=TaskName.SHOP_BUILD.value, soft_time_limit=600)
def build_task(idea_id: str) -> dict[str, str]:
    db = SessionLocal()
    try:
        idea = db.get(ProductIdea, uuid.UUID(idea_id))
        if idea is None:
            return {"status": "idea_not_found"}
        spec = structured(BUILD_PROMPT.format(title=idea.title), PrintableSpec)
        if spec is None:
            msg = "Printable specification generation returned None"
            raise RuntimeError(msg)
        body = html_for(spec)
        slug = f"rs-{idea.id.hex[:12]}"
        product = db.scalar(select(Product).where(Product.slug == slug))
        if product is None:
            product = Product(
                slug=slug,
                title=idea.title,
                description=idea.term,
                kind=ProductKind.PRINTABLE.value,
                price_cents=clamp_price(900),
                status=ProductStatus.DRAFT.value,
            )
            db.add(product)
            db.flush()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a4 = root / "a4.pdf"
            letter = root / "letter.pdf"
            render_pdf(body, page_css("A4"), a4)
            render_pdf(body, page_css("letter"), letter)
            validate_assets(a4, len(spec.pages))
            validate_assets(letter, len(spec.pages))
            storage.ensure_bucket_exists()
            storage.put(
                f"printables/{product.slug}-a4.pdf",
                a4.read_bytes(),
                "application/pdf",
            )
            storage.put(
                f"printables/{product.slug}-letter.pdf",
                letter.read_bytes(),
                "application/pdf",
            )
            product.asset_pdf = f"printables/{product.slug}-a4.pdf"
            product.extras = {
                "letter_pdf": f"printables/{product.slug}-letter.pdf",
                "idea_id": str(idea.id),
            }
        db.commit()
        celery_app.send_task(TaskName.SHOP_LIST.value, args=[str(product.id)])
        return {"product_id": str(product.id)}
    finally:
        db.close()
