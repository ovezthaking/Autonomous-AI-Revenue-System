"""Markdown -> PDF/EPUB layout helpers (pandoc + WeasyPrint, no LaTeX)."""

import html
import subprocess
from pathlib import Path

from pypdf import PdfReader
from revenue_swarm.models.ebook_chapter import EbookChapter
from revenue_swarm.models.product import Product

CSS_PATH = Path(__file__).parent / "style.css"
MIN_PDF_BYTES = 50_000


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
    size = pdf_path.stat().st_size
    pages = len(PdfReader(str(pdf_path)).pages)
    if size <= MIN_PDF_BYTES or pages < chapter_count:
        msg = f"pdf too small: {size} bytes, {pages} pages"
        raise RuntimeError(msg)
