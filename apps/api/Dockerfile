# TCG Chart API — uv monorepo image for Railway/Render.
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/
COPY apps/ml/pyproject.toml apps/ml/
COPY packages/sdk-py/pyproject.toml packages/sdk-py/
COPY packages/agents/pyproject.toml packages/agents/

COPY apps/api apps/api
COPY apps/ml apps/ml
COPY packages/sdk-py packages/sdk-py
COPY packages/agents packages/agents

RUN uv sync --frozen --package tcgscan-api --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Run migrations then start the API (override CMD on platforms that run migrate separately).
CMD sh -c "cd apps/api && alembic upgrade head && uvicorn tcgscan_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"
