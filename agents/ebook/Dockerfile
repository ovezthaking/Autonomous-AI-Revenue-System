FROM python:3.14-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /bin/

# pandoc + pango/cairo/fonts for WeasyPrint (no LaTeX on purpose)
RUN apt-get update && apt-get install -y --no-install-recommends \
    pandoc libpango-1.0-0 libpangoft2-1.0-0 libcairo2 fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock ./
COPY shared/pyproject.toml shared/pyproject.toml
COPY backend/pyproject.toml backend/pyproject.toml
COPY agents/research/pyproject.toml agents/research/pyproject.toml
COPY agents/content/pyproject.toml agents/content/pyproject.toml
COPY agents/ebook/pyproject.toml agents/ebook/pyproject.toml

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-workspace --package ebook-agent

COPY shared shared
COPY agents/ebook agents/ebook

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package ebook-agent

CMD ["celery", "-A", "ebook_agent.worker:celery_app", "worker", \
     "--queues=ebook", "--concurrency=1", "--loglevel=info"]
