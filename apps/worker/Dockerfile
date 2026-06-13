# TCG Chart worker — cron-friendly image (no Temporal required for launch).
FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/
COPY apps/worker/pyproject.toml apps/worker/
COPY apps/ml/pyproject.toml apps/ml/
COPY packages/sdk-py/pyproject.toml packages/sdk-py/
COPY packages/agents/pyproject.toml packages/agents/

COPY apps/api apps/api
COPY apps/worker apps/worker
COPY apps/ml apps/ml
COPY packages/sdk-py packages/sdk-py
COPY packages/agents packages/agents

RUN uv sync --frozen --package tcgscan-worker --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Override per Railway cron job, e.g.:
#   python -m tcgscan_worker ingest:pricing --game pokemon
#   python -m tcgscan_worker rollup:daily
#   python -m tcgscan_worker ingest:catalog --game pokemon
CMD ["python", "-m", "tcgscan_worker", "--help"]
