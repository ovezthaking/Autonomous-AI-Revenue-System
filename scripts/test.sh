#!/bin/sh
set -eu
cd "$(dirname "$0")/.."

# --directory makes pytest use that package's pyproject.toml as rootdir.
uv run --directory backend --package revenue-swarm-backend pytest
uv run --directory agents/research --package research-agent pytest
uv run --directory agents/content --package content-agent pytest
