FROM python:3.14-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /bin/

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

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-workspace --package content-agent

COPY shared shared
COPY agents/content agents/content

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package content-agent

CMD ["celery", "-A", "content_agent.worker:celery_app", "worker", \
     "--queues=content", "--concurrency=1", "--loglevel=info"]
