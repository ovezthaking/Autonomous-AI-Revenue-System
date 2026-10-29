"""Markdown -> PDF/EPUB layout helpers (pandoc + WeasyPrint, no LaTeX)."""

import html
import subprocess
from pathlib import Path

from revenue_swarm.models.ebook_chapter import EbookChapter
from revenue_swarm.models.product import Product
from revenue_swarm.render.pdf import (
    MIN_PDF_BYTES,
    render_pdf,
    validate_pdf,
)

CSS_PATH = Path(__file__).parent / "style.css"


def cover_html(product: Product) -> str:
    title = html.escape(product.title)
    subtitle = html.escape(product.subtitle or "")
    return (
        f"<section class='cover'><h1>{title}</h1><p>{subtitle}</p></section>"
    )


def build_markdown(product: Product, chapters: list[EbookChapter]) -> str:
    parts = [cover_html(product)]
    for chapter in chapters:
        parts.append(f"# {chapter.title}\n\n{chapter.body or ''}")
    return "\n\n".join(parts)


def pandoc(
    product: Product, md_path: Path, out_path: Path, *, pdf: bool
) -> None:
    command = [
        "pandoc",
        str(md_path),
        "--metadata",
        f"title={product.title}",
        "-o",
        str(out_path),
    ]
    if pdf:
        command[2:2] = ["--css", str(CSS_PATH), "--pdf-engine=weasyprint"]
    subprocess.run(command, check=True, timeout=300)  # noqa: S603


def validate_assets(pdf_path: Path, chapter_count: int) -> None:
    validate_pdf(pdf_path, min_pages=chapter_count, min_bytes=MIN_PDF_BYTES)


__all__ = [
    "CSS_PATH",
    "MIN_PDF_BYTES",
    "build_markdown",
    "cover_html",
    "pandoc",
    "render_pdf",
    "validate_assets",
]
