"""Structured printable specification and HTML/CSS composition."""

import html
from pathlib import Path

from pydantic import BaseModel
from revenue_swarm import config, llm as shared_llm

TEMPLATE_DIR = Path(__file__).parent / "templates"
TEMPLATE_PATH = TEMPLATE_DIR / "printable.html"
CSS_PATH = TEMPLATE_DIR / "printable.css"

BUILD_PROMPT = (
    "Create a structured multi-page printable worksheet/planner specification "
    "for the product titled: {title}. Provide clear headings and actionable "
    "sections for each page."
)


class PageSpec(BaseModel):
    heading: str
    sections: list[str]


class PrintableSpec(BaseModel):
    title: str
    pages: list[PageSpec]


def _stub_spec(prompt: str) -> PrintableSpec:
    raw = prompt.split("titled:", 1)[-1].split(".", 1)[0].strip()
    title = raw or "Planner"
    return PrintableSpec(
        title=title,
        pages=[
            PageSpec(
                heading=f"{title} — Overview & Goals",
                sections=[
                    "Primary Objective & Priority Targets",
                    "Key Milestones & Weekly Focus",
                    "Action Checklist & Preparation Notes",
                ],
            ),
            PageSpec(
                heading=f"{title} — Daily & Weekly Tracker",
                sections=[
                    "Schedule & Time Blocks",
                    "Habit & Progress Metrics",
                    "Review & Adjustments",
                ],
            ),
        ],
    )


def structured(
    prompt: str, schema: type[PrintableSpec]
) -> PrintableSpec | None:
    if config.LLM_STUB:
        return _stub_spec(prompt)
    return shared_llm.structured(prompt, schema)


def html_for(spec: PrintableSpec) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    pages: list[str] = []
    for idx, page in enumerate(spec.pages):
        blocks = "".join(
            f"<section><h2>{html.escape(line)}</h2>"
            "<div class='lines'><div class='line'></div>"
            "<div class='line'></div><div class='line'></div></div></section>"
            for line in page.sections
        )
        cls = " class='page-break'" if idx > 0 else ""
        pages.append(
            f"<article{cls}><h1>{html.escape(page.heading)}</h1>{blocks}</article>"
        )
    return template.replace("{{pages}}", "\n".join(pages))


def page_css(size: str) -> str:
    base = CSS_PATH.read_text(encoding="utf-8")
    return base + f"\n@page {{ size: {size}; margin: 12mm; }}\n"
