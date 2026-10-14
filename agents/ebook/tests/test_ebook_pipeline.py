import shutil
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest
from ebook_agent.assemble import (
    build_markdown,
    cover_html,
    pandoc,
    validate_assets,
)
from ebook_agent.schemas import Outline, OutlineChapter, Topic, TopicList
from ebook_agent.tasks import (
    assemble_task,
    outline_task,
    propose_topics_task,
    write_task,
)
from pypdf import PdfReader, PdfWriter
from revenue_swarm.config import EBOOK_MAX_CHAPTERS
from revenue_swarm.enums import ProductStatus
from revenue_swarm.models.ebook_chapter import EbookChapter
from revenue_swarm.models.product import Product
from revenue_swarm.tasks import TaskName
from sqlalchemy import func, select, text


def _too_many() -> Outline:
    return Outline(
        chapters=[
            OutlineChapter(title=f"Chapter {i}", brief=f"Brief {i}")
            for i in range(1, EBOOK_MAX_CHAPTERS + 5)
        ]
    )


def _two_chapters(db) -> tuple[Product, EbookChapter, EbookChapter]:
    product = Product(
        slug="guide-two",
        title="Guide",
        price_cents=1900,
        status=ProductStatus.OUTLINED.value,
    )
    db.add(product)
    db.commit()
    written = EbookChapter(
        product_id=product.id,
        position=1,
        title="Intro",
        brief="Intro brief",
        body="Existing body.",
        status="written",
        tokens_used=120,
    )
    pending = EbookChapter(
        product_id=product.id,
        position=2,
        title="Deep Dive",
        brief="Deep brief",
        status="pending",
    )
    db.add_all([written, pending])
    db.commit()
    return product, written, pending


def _make_valid_pdf(path: Path, pages: int, min_bytes: int = 60_000) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=420, height=595)
    with path.open("wb") as fh:
        writer.write(fh)
    current = path.stat().st_size
    if current < min_bytes:
        with path.open("ab") as fh:
            fh.write(b"%" + b"0" * (min_bytes - current))


# --- pure / non-DB unit tests ---------------------------------------------


def test_cover_html_escapes_title_and_subtitle():
    product = Product(
        slug="sec",
        title="A & B <Guide>",
        subtitle="Sub <1>",
        price_cents=1900,
    )
    rendered = cover_html(product)
    assert "A &amp; B &lt;Guide&gt;" in rendered
    assert "Sub &lt;1&gt;" in rendered


def test_build_markdown_includes_cover_and_chapters():
    product = Product(slug="md", title="Book Title", price_cents=1900)
    ch1 = EbookChapter(position=1, title="One", brief="b1", body="Body one.")
    ch2 = EbookChapter(position=2, title="Two", brief="b2", body="Body two.")

    md = build_markdown(product, [ch1, ch2])

    assert "<section class='cover'>" in md
    assert "# One\n\nBody one." in md
    assert "# Two\n\nBody two." in md


def test_validate_assets_accepts_valid_pdf_and_rejects_small_or_short(
    tmp_path,
):
    good = tmp_path / "good.pdf"
    _make_valid_pdf(good, pages=3, min_bytes=60_000)
    validate_assets(good, chapter_count=3)

    too_small = tmp_path / "small.pdf"
    _make_valid_pdf(too_small, pages=3, min_bytes=1_000)
    with pytest.raises(RuntimeError, match="pdf too small"):
        validate_assets(too_small, chapter_count=3)

    too_few_pages = tmp_path / "short.pdf"
    _make_valid_pdf(too_few_pages, pages=1, min_bytes=60_000)
    with pytest.raises(RuntimeError, match="pdf too small"):
        validate_assets(too_few_pages, chapter_count=3)


# --- database / pipeline integration tests --------------------------------


@pytest.mark.integration
def test_propose_topics_creates_unique_slugs_for_duplicate_titles(
    db, make_program
):
    make_program(status="approved", name="HelpDeskPro")
    dup_topics = TopicList(
        topics=[
            Topic(title="Same Title", angle="Angle 1"),
            Topic(title="Same Title", angle="Angle 2"),
        ]
    )
    with patch("ebook_agent.tasks.structured", return_value=dup_topics):
        result = propose_topics_task("help desk")

    assert result == {"created": 2}
    rows = db.scalars(select(Product)).all()
    assert len(rows) == 2
    assert rows[0].slug != rows[1].slug


@pytest.mark.integration
def test_outline_stops_at_max_chapters_and_is_idempotent(db):
    product = Product(
        slug="guide", title="Guide", price_cents=1900, status="draft"
    )
    db.add(product)
    db.commit()

    with patch("ebook_agent.tasks.structured", return_value=_too_many()):
        first = outline_task(str(product.id))
        db.expire_all()
        product.status = ProductStatus.OUTLINING.value
        db.commit()
        second = outline_task(str(product.id))

    count = db.scalar(
        select(func.count())
        .select_from(EbookChapter)
        .where(EbookChapter.product_id == product.id)
    )
    assert first == {"chapters": EBOOK_MAX_CHAPTERS}
    assert second == {"chapters": EBOOK_MAX_CHAPTERS}
    assert count == EBOOK_MAX_CHAPTERS


@pytest.mark.integration
def test_write_skips_written_records_tokens_and_queues_assemble(
    db, no_celery_broker
):
    product, written, pending = _two_chapters(db)

    with patch(
        "ebook_agent.tasks.chat_with_usage",
        return_value=("Chapter body.", 350),
    ) as mocked_chat:
        summary = write_task(str(product.id))

    db.expire_all()
    assert mocked_chat.call_count == 1
    prompt_sent = mocked_chat.call_args[0][0]
    assert "1. Intro: Intro brief" in prompt_sent
    assert written.body == "Existing body."
    assert pending.status == "written"
    assert pending.body == "Chapter body."
    assert pending.tokens_used == 350
    assert summary["written"] == 2
    assert summary["assemble_queued"] == 1
    assert no_celery_broker == [(TaskName.EBOOK_ASSEMBLE, [str(product.id)])]


@pytest.mark.integration
def test_write_single_failure_does_not_abort_remaining_chapters(
    db, no_celery_broker
):
    product = Product(
        slug="guide-fail",
        title="Guide",
        price_cents=1900,
        status=ProductStatus.OUTLINED.value,
    )
    db.add(product)
    db.commit()
    for pos in (1, 2):
        db.add(
            EbookChapter(
                product_id=product.id,
                position=pos,
                title=f"Ch {pos}",
                brief=f"Brief {pos}",
                status="pending",
            )
        )
    db.commit()

    calls = {"n": 0}

    def _flaky_chat(prompt: str, temperature: float = 0.2) -> tuple[str, int]:
        calls["n"] += 1
        if calls["n"] == 1:
            msg = "model 500 error"
            raise RuntimeError(msg)
        return "Recovered chapter.", 200

    with patch("ebook_agent.tasks.chat_with_usage", side_effect=_flaky_chat):
        summary = write_task(str(product.id))

    db.expire_all()
    chapters = db.scalars(
        select(EbookChapter)
        .where(EbookChapter.product_id == product.id)
        .order_by(EbookChapter.position.asc())
    ).all()
    assert chapters[0].status == "failed"
    assert "model 500 error" in (chapters[0].error or "")
    assert chapters[1].status == "written"
    assert summary["written"] == 1
    assert summary["failed"] == 1
    assert no_celery_broker == []

    # Retrying failed chapters re-runs only chapter 1 and then queues assemble
    with patch(
        "ebook_agent.tasks.chat_with_usage",
        return_value=("Fixed chapter 1.", 180),
    ) as retry_chat:
        retry_summary = write_task(str(product.id), retry_failed=True)

    assert retry_chat.call_count == 1
    assert retry_summary["written"] == 2
    assert retry_summary["assemble_queued"] == 1


@pytest.mark.integration
def test_write_stops_when_token_budget_is_exhausted(
    db, monkeypatch, no_celery_broker
):
    monkeypatch.setattr("ebook_agent.tasks.EBOOK_MAX_TOKENS_PER_BOOK", 100)
    product, _, pending = _two_chapters(db)  # written already has 120 tokens

    with patch(
        "ebook_agent.tasks.chat_with_usage",
        return_value=("Should not run", 50),
    ) as mocked_chat:
        summary = write_task(str(product.id))

    db.expire_all()
    assert mocked_chat.call_count == 0
    assert pending.status == "pending"
    assert summary["budget_exhausted"] == 1
    assert no_celery_broker == []


@pytest.mark.integration
def test_assemble_task_uploads_pdf_and_epub_and_marks_assembled(
    db, monkeypatch
):
    product = Product(
        slug="guide-asm",
        title="Assembled Guide",
        price_cents=1900,
        status=ProductStatus.WRITING.value,
    )
    db.add(product)
    db.commit()
    for pos in (1, 2):
        db.add(
            EbookChapter(
                product_id=product.id,
                position=pos,
                title=f"Ch {pos}",
                brief=f"Brief {pos}",
                body=f"Content {pos}",
                status="written",
            )
        )
    db.commit()

    uploaded: dict[str, tuple[bytes, str]] = {}

    def _fake_pandoc(prod, md_path: Path, out_path: Path, *, pdf: bool):
        if pdf:
            _make_valid_pdf(out_path, pages=2, min_bytes=60_000)
        else:
            out_path.write_bytes(b"PK\x03\x04fake-epub-archive")

    monkeypatch.setattr("ebook_agent.tasks.pandoc", _fake_pandoc)
    monkeypatch.setattr(
        "ebook_agent.tasks.storage.ensure_bucket_exists", lambda: None
    )
    monkeypatch.setattr(
        "ebook_agent.tasks.storage.put",
        lambda key, data, ctype: uploaded.__setitem__(key, (data, ctype)),
    )

    result = assemble_task(str(product.id))

    db.expire_all()
    refreshed = db.get(Product, product.id)
    assert refreshed.status == ProductStatus.ASSEMBLED.value
    assert refreshed.asset_pdf == "ebooks/guide-asm.pdf"
    assert refreshed.asset_epub == "ebooks/guide-asm.epub"
    assert result == {
        "pdf": "ebooks/guide-asm.pdf",
        "epub": "ebooks/guide-asm.epub",
    }
    assert set(uploaded) == {"ebooks/guide-asm.pdf", "ebooks/guide-asm.epub"}


@pytest.mark.integration
def test_write_survives_a_database_error_inside_a_chapter(
    db, no_celery_broker
):
    """A failed SQL statement poisons the session until it is rolled back.

    The chapter must still be recorded as failed and the next one written.
    """
    product = Product(
        slug="guide-dberr",
        title="Guide",
        price_cents=1900,
        status=ProductStatus.OUTLINED.value,
    )
    db.add(product)
    db.commit()
    for pos in (1, 2):
        db.add(
            EbookChapter(
                product_id=product.id,
                position=pos,
                title=f"Ch {pos}",
                brief=f"Brief {pos}",
                status="pending",
            )
        )
    db.commit()

    calls = {"n": 0}

    def _write_chapter(session, prod, chapter, context):
        calls["n"] += 1
        if calls["n"] == 1:
            session.execute(text("SELECT 1/0"))  # aborts the transaction
        return "Fine chapter.", 100

    with patch("ebook_agent.tasks.write_chapter", side_effect=_write_chapter):
        summary = write_task(str(product.id))

    db.expire_all()
    chapters = db.scalars(
        select(EbookChapter)
        .where(EbookChapter.product_id == product.id)
        .order_by(EbookChapter.position.asc())
    ).all()
    assert chapters[0].status == "failed"
    assert chapters[1].status == "written"
    assert summary["failed"] == 1
    assert summary["written"] == 1


@pytest.mark.skipif(
    shutil.which("pandoc") is None, reason="pandoc is not installed"
)
def test_real_pandoc_builds_a_readable_pdf_and_epub(tmp_path):
    """Exercises the real pandoc + WeasyPrint stack (no mocks)."""
    product = Product(
        slug="real", title="Real Book", subtitle="Sub", price_cents=1900
    )
    chapters = [
        EbookChapter(
            position=i,
            title=f"Chapter {i}",
            brief="b",
            body="Lorem ipsum dolor sit amet. " * 80,
        )
        for i in (1, 2, 3)
    ]
    md_path = tmp_path / "book.md"
    md_path.write_text(build_markdown(product, chapters), encoding="utf-8")
    pdf_path = tmp_path / "book.pdf"
    epub_path = tmp_path / "book.epub"

    pandoc(product, md_path, pdf_path, pdf=True)
    pandoc(product, md_path, epub_path, pdf=False)

    assert len(PdfReader(str(pdf_path)).pages) >= len(chapters)
    assert zipfile.is_zipfile(epub_path)
