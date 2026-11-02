"""Shop printable tests: A4 + Letter PDFs, price, and listing cap."""

import shutil
import uuid

import pytest
from pypdf import PdfReader
from revenue_swarm.config import SHOP_PRICE_MAX_CENTS, SHOP_PRICE_MIN_CENTS
from revenue_swarm.enums import IdeaStatus, ListingStatus, ProductKind
from revenue_swarm.models.product import Product
from revenue_swarm.models.product_idea import ProductIdea
from revenue_swarm.models.product_listing import ProductListing
from revenue_swarm.render.pdf import render_pdf
from shop_agent.build import PageSpec, PrintableSpec, html_for, page_css
from shop_agent.listing import clamp_price
from shop_agent.tasks import build_task, list_task
from sqlalchemy import func, select


def test_price_is_clamped():
    assert clamp_price(1) == SHOP_PRICE_MIN_CENTS
    assert clamp_price(999_00) == SHOP_PRICE_MAX_CENTS


@pytest.mark.skipif(
    shutil.which("pandoc") is None, reason="pandoc is not installed"
)
def test_printable_renders_a4_and_letter_with_distinct_page_dimensions(
    tmp_path,
):
    spec = PrintableSpec(
        title="Budget Planner",
        pages=[
            PageSpec(
                heading="Monthly Overview",
                sections=["Income Sources", "Fixed Expenses", "Savings Goals"],
            ),
            PageSpec(
                heading="Weekly Expense Tracker",
                sections=["Week 1", "Week 2", "Week 3", "Week 4"],
            ),
        ],
    )
    body = html_for(spec)
    a4_path = tmp_path / "a4.pdf"
    letter_path = tmp_path / "letter.pdf"

    render_pdf(body, page_css("A4"), a4_path)
    render_pdf(body, page_css("letter"), letter_path)

    a4_reader = PdfReader(str(a4_path))
    letter_reader = PdfReader(str(letter_path))

    assert len(a4_reader.pages) >= 2
    assert len(letter_reader.pages) >= 2

    a4_box = a4_reader.pages[0].mediabox
    letter_box = letter_reader.pages[0].mediabox

    # A4 is ~595 x 842 pt; US Letter is 612 x 792 pt
    assert abs(float(a4_box.width) - 595.28) < 2.0
    assert abs(float(a4_box.height) - 841.89) < 2.0
    assert abs(float(letter_box.width) - 612.0) < 2.0
    assert abs(float(letter_box.height) - 792.0) < 2.0


@pytest.mark.integration
def test_build_task_and_daily_listing_limit(db, monkeypatch, no_celery_broker):
    uploaded: dict[str, bytes] = {}
    monkeypatch.setattr(
        "shop_agent.tasks.storage.ensure_bucket_exists", lambda: None
    )
    monkeypatch.setattr(
        "shop_agent.tasks.storage.put",
        lambda key, data, ctype: uploaded.__setitem__(key, data),
    )

    idea = ProductIdea(
        term="monthly budget planner printable",
        title="Monthly Budget Planner",
        kind=ProductKind.PRINTABLE.value,
        score=0.85,
        score_breakdown={"own_fit": 0.35, "demand": 0.25},
        status=IdeaStatus.APPROVED.value,
    )
    db.add(idea)
    db.commit()

    res = build_task(str(idea.id))
    product_id = res["product_id"]
    product = db.get(Product, uuid.UUID(product_id))
    assert product is not None
    assert product.asset_pdf == f"printables/{product.slug}-a4.pdf"
    assert (product.extras or {}).get(
        "letter_pdf"
    ) == f"printables/{product.slug}-letter.pdf"
    assert set(uploaded) == {
        f"printables/{product.slug}-a4.pdf",
        f"printables/{product.slug}-letter.pdf",
    }

    # Respect SHOP_MAX_NEW_LISTINGS_PER_DAY
    monkeypatch.setattr("shop_agent.tasks.SHOP_MAX_NEW_LISTINGS_PER_DAY", 1)
    first_list = list_task(product_id)
    assert first_list["status"] == ListingStatus.DRAFT.value

    second_product = Product(
        slug=f"rs-{uuid.uuid4().hex[:12]}",
        title="Second Printable",
        kind=ProductKind.PRINTABLE.value,
        price_cents=900,
    )
    db.add(second_product)
    db.commit()

    capped = list_task(str(second_product.id))
    assert capped == {"status": "daily_limit_reached"}
    assert db.scalar(select(func.count()).select_from(ProductListing)) == 1
