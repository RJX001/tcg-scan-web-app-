FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy entire monorepo (Railway build context = repo root)
COPY . .

RUN uv sync --frozen --package tcgscan-api --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["sh", "-c", "cd /app && alembic --config apps/api/alembic.ini upgrade head && uvicorn tcgscan_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
