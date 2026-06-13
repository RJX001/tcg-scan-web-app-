FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy entire monorepo (Railway build context = repo root)
COPY . .

RUN uv sync --frozen --package tcgscan-worker --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Override per Railway cron job, e.g.:
#   python -m tcgscan_worker ingest:pricing --game pokemon
#   python -m tcgscan_worker rollup:daily
#   python -m tcgscan_worker ingest:catalog --game pokemon
CMD ["python", "-m", "tcgscan_worker", "--help"]
