"""Shared HTML/CSS -> PDF rendering and validation helpers (WeasyPrint)."""

import subprocess
from pathlib import Path

MIN_PDF_BYTES = 5_000


def render_pdf(html: str, css: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    html_path = out.with_suffix(".html")
    html_path.write_text(html, encoding="utf-8")
    css_path = out.with_suffix(".css")
    css_path.write_text(css, encoding="utf-8")
    subprocess.run(
        [
            "pandoc",
            str(html_path),
            "--css",
            str(css_path),
            "--pdf-engine=weasyprint",
            "-o",
            str(out),
        ],
        check=True,
        timeout=300,
    )  # noqa: S603


def validate_pdf(
    pdf_path: Path, min_pages: int = 1, min_bytes: int = MIN_PDF_BYTES
) -> None:
    from pypdf import PdfReader

    size = pdf_path.stat().st_size
    pages = len(PdfReader(str(pdf_path)).pages)
    if size <= min_bytes or pages < min_pages:
        msg = f"pdf too small: {size} bytes, {pages} pages"
        raise RuntimeError(msg)


def validate_assets(
    pdf_path: Path, page_count: int, min_bytes: int = MIN_PDF_BYTES
) -> None:
    validate_pdf(pdf_path, min_pages=page_count, min_bytes=min_bytes)
