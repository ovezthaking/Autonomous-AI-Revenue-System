import re
import tempfile
import unicodedata
import uuid
from pathlib import Path

from celery.exceptions import SoftTimeLimitExceeded
from celery.utils.log import logger
from revenue_swarm import storage
from revenue_swarm.celery import celery_app
from revenue_swarm.config import (
    EBOOK_ENABLED,
    EBOOK_MAX_CHAPTERS,
    EBOOK_MAX_TOKENS_PER_BOOK,
    LLM_STUB,
)
from revenue_swarm.db import SessionLocal
from revenue_swarm.enums import ProductStatus, ProgramStatus
from revenue_swarm.llm import chat_with_usage, structured
from revenue_swarm.models.affiliate_program import AffiliateProgram
from revenue_swarm.models.ebook_chapter import EbookChapter
from revenue_swarm.models.product import Product
from revenue_swarm.tasks import TaskName
from sqlalchemy import select
from sqlalchemy.orm import Session

from ebook_agent.assemble import build_markdown, pandoc, validate_assets
from ebook_agent.redaction import redact
from ebook_agent.schemas import Outline, OutlineChapter, Topic, TopicList

DEFAULT_PRICE_CENTS = 1900


class BudgetExhaustedError(RuntimeError):
    """Per-book token budget is spent; stop writing, keep chapters pending."""


def _slug(title: str) -> str:
    ascii_title = (
        unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    )
    base = re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")[:60]
    return f"{base or 'ebook'}-{uuid.uuid4().hex[:6]}"


def _stub_topics(niche: str) -> TopicList:
    return TopicList(
        topics=[Topic(title=f"{niche}: a practical guide", angle="stub angle")]
    )


def _stub_outline() -> Outline:
    return Outline(
        chapters=[
            OutlineChapter(title=f"Stub chapter {i}", brief="stub brief")
            for i in (1, 2, 3)
        ]
    )


# --- propose_topics -------------------------------------------------------


@celery_app.task(name=TaskName.EBOOK_PROPOSE.value)
def propose_topics_task(niche: str) -> dict[str, int]:
    if not EBOOK_ENABLED:
        return {"created": 0}
    db = SessionLocal()
    try:
        titles = list(
            db.scalars(
                select(AffiliateProgram.name).where(
                    AffiliateProgram.status == ProgramStatus.APPROVED.value
                )
            ).all()
        )
        prompt = (
            "Propose 3 ebook titles for this niche. "
            f"Niche: {niche}. Related products: {', '.join(titles)}."
        )
        ideas = structured(prompt, TopicList)
        if ideas is None and LLM_STUB:
            ideas = _stub_topics(niche)
        created = 0
        for idea in ideas.topics if ideas else []:
            db.add(
                Product(
                    slug=_slug(idea.title),
                    title=idea.title,
                    description=idea.angle,
                    price_cents=DEFAULT_PRICE_CENTS,
                    status=ProductStatus.DRAFT.value,
                )
            )
            created += 1
        db.commit()
        return {"created": created}
    finally:
        db.close()


# --- outline --------------------------------------------------------------


@celery_app.task(name=TaskName.EBOOK_OUTLINE.value)
def outline_task(product_id: str) -> dict[str, int]:
    db = SessionLocal()
    try:
        product = db.get(Product, uuid.UUID(product_id))
        if product is None:
            return {"chapters": 0}
        if product.status not in (
            ProductStatus.DRAFT.value,
            ProductStatus.OUTLINING.value,
        ):
            return {"chapters": 0}

        existing = _chapter_count(db, product.id)
        if existing:
            product.status = ProductStatus.OUTLINED.value
            db.commit()
            return {"chapters": existing}

        prompt = (
            f"Outline at most {EBOOK_MAX_CHAPTERS} chapters for "
            f"{product.title}. {product.description or ''}"
        )
        outline = structured(prompt, Outline)
        if outline is None and LLM_STUB:
            outline = _stub_outline()
        chapters = (outline.chapters if outline else [])[:EBOOK_MAX_CHAPTERS]
        if not chapters:
            # let a human re-approve instead of leaving the book stuck
            product.status = ProductStatus.DRAFT.value
            db.commit()
            return {"chapters": 0}
        for index, chapter in enumerate(chapters, start=1):
            db.add(
                EbookChapter(
                    product_id=product.id,
                    position=index,
                    title=chapter.title,
                    brief=chapter.brief,
                    status="pending",
                )
            )
        product.status = ProductStatus.OUTLINED.value
        db.commit()
        return {"chapters": len(chapters)}
    finally:
        db.close()


def _chapter_count(db: Session, product_id: uuid.UUID) -> int:
    return len(
        db.scalars(
            select(EbookChapter.id).where(
                EbookChapter.product_id == product_id
            )
        ).all()
    )


# --- write ----------------------------------------------------------------


def _chapters_with_status(
    db: Session, product_id: uuid.UUID, status: str
) -> list[EbookChapter]:
    stmt = (
        select(EbookChapter)
        .where(
            EbookChapter.product_id == product_id,
            EbookChapter.status == status,
        )
        .order_by(EbookChapter.position.asc())
    )
    return list(db.scalars(stmt).all())


def _pending_chapters(
    db: Session, product_id: uuid.UUID
) -> list[EbookChapter]:
    return _chapters_with_status(db, product_id, "pending")


def _recap(db: Session, product_id: uuid.UUID) -> str:
    return "\n".join(
        f"{chapter.position}. {chapter.title}: {chapter.brief}"
        for chapter in _chapters_with_status(db, product_id, "written")
    )


def _tokens_spent(db: Session, product_id: uuid.UUID) -> int:
    rows = db.scalars(
        select(EbookChapter.tokens_used).where(
            EbookChapter.product_id == product_id
        )
    ).all()
    return sum(value or 0 for value in rows)


def write_chapter(
    db: Session, product: Product, chapter: EbookChapter, context: str
) -> tuple[str, int]:
    if _tokens_spent(db, product.id) >= EBOOK_MAX_TOKENS_PER_BOOK:
        msg = "token budget exhausted"
        raise BudgetExhaustedError(msg)
    prompt = (
        f"Write chapter {chapter.position}: {chapter.title}.\n"
        f"Brief: {chapter.brief}\n"
        "Do not repeat material already covered by earlier chapters.\n"
        f"Earlier chapters (title: brief):\n{context}"
    )
    return chat_with_usage(prompt, temperature=0.2)


def _summary(db: Session, product_id: uuid.UUID) -> dict[str, int]:
    rows = db.scalars(
        select(EbookChapter).where(EbookChapter.product_id == product_id)
    ).all()
    return {
        "written": sum(row.status == "written" for row in rows),
        "failed": sum(row.status == "failed" for row in rows),
        "pending": sum(row.status == "pending" for row in rows),
    }


@celery_app.task(
    name=TaskName.EBOOK_WRITE.value, soft_time_limit=3600, time_limit=3700
)
def write_task(product_id: str, retry_failed: bool = False) -> dict:
    db = SessionLocal()
    try:
        product = db.get(Product, uuid.UUID(product_id))
        if product is None or product.status not in (
            ProductStatus.OUTLINED.value,
            ProductStatus.WRITING.value,
        ):
            return {"status": "skipped"}
        product.status = ProductStatus.WRITING.value
        if retry_failed:  # re-run only the chapters that failed
            for chapter in _chapters_with_status(db, product.id, "failed"):
                chapter.status = "pending"
                chapter.error = None
        db.commit()

        budget_exhausted = False
        for chapter in _pending_chapters(db, product.id):
            chapter_id = chapter.id
            position = chapter.position
            try:
                body, tokens = write_chapter(
                    db, product, chapter, context=_recap(db, product.id)
                )
                chapter.body = body
                chapter.tokens_used = tokens
                chapter.status = "written"
            except BudgetExhaustedError:
                budget_exhausted = True
                break
            except SoftTimeLimitExceeded:
                db.rollback()
                raise
            except Exception as e:  # noqa: BLE001 — one bad chapter != dead book
                db.rollback()
                failed = db.get(EbookChapter, chapter_id)
                failed.status = "failed"
                failed.error = redact(str(e))
                logger.warning("chapter %s failed", position)
            db.commit()  # commit after EVERY chapter

        summary = _summary(db, product.id)
        summary["budget_exhausted"] = int(budget_exhausted)
        total = sum(summary[key] for key in ("written", "failed", "pending"))
        if total and summary["written"] == total:
            celery_app.send_task(
                TaskName.EBOOK_ASSEMBLE.value, args=[str(product.id)]
            )
            summary["assemble_queued"] = 1
        return summary
    finally:
        db.close()


# --- assemble -------------------------------------------------------------


@celery_app.task(name=TaskName.EBOOK_ASSEMBLE.value, soft_time_limit=600)
def assemble_task(product_id: str) -> dict[str, str]:
    db = SessionLocal()
    try:
        product = db.get(Product, uuid.UUID(product_id))
        if product is None:
            return {"status": "not_found"}
        chapters = _chapters_with_status(db, product.id, "written")
        if not chapters or len(chapters) != _chapter_count(db, product.id):
            return {"status": "chapters_incomplete"}

        pdf_key = f"ebooks/{product.slug}.pdf"
        epub_key = f"ebooks/{product.slug}.epub"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            md_path = root / "book.md"
            md_path.write_text(
                build_markdown(product, chapters), encoding="utf-8"
            )
            pdf_path = root / "book.pdf"
            epub_path = root / "book.epub"
            pandoc(product, md_path, pdf_path, pdf=True)
            pandoc(product, md_path, epub_path, pdf=False)
            validate_assets(pdf_path, len(chapters))
            storage.ensure_bucket_exists()  # fresh MinIO has no bucket
            storage.put(pdf_key, pdf_path.read_bytes(), "application/pdf")
            storage.put(
                epub_key, epub_path.read_bytes(), "application/epub+zip"
            )
        product.asset_pdf = pdf_key
        product.asset_epub = epub_key
        product.status = ProductStatus.ASSEMBLED.value
        db.commit()
        return {"pdf": pdf_key, "epub": epub_key}
    finally:
        db.close()
