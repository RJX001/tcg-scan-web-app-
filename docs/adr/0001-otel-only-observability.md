# ADR-0001: OTEL-only observability for the API (remove Sentry)

- **Status**: Accepted
- **Date**: 2026-07-18

## Context

The API had two overlapping telemetry paths:

1. OpenTelemetry (traces + metrics) exported via OTLP HTTP to Grafana Alloy, which fans out to Grafana Cloud (Mimir / Tempo / Loki). Auto-instrumentation only (FastAPI + httpx); no custom spans, metrics, or log export.
2. `sentry-sdk` init in `telemetry.py` with `traces_sample_rate=0.1`. In practice this never ran in production: the package sat in dev-only dependency groups while the Docker image builds with `uv sync --no-dev`, so the import always failed (silently swallowed).

`docs/TCG_Scan_Phase1.md` §12.8 calls for Sentry on web + api + worker. This ADR records the deliberate deviation.

## Decision drivers

- One instrumentation layer to maintain; the team is pre-beta and small.
- Backend portability: Grafana Cloud, New Relic, and (partially) Sentry all ingest OTLP, so vendor choice should be an exporter-config decision, not a code decision.
- Sentry's OTLP ingestion (GA May 2026) drops span events — OTel-recorded exceptions never become Sentry Issues — and does not accept OTLP metrics. Feeding Sentry from the OTEL pipeline therefore cannot replace the Sentry SDK, and running two tracing SDKs in one process is overlap we don't want.
- The Sentry integration was dead code in production anyway; "removing" it loses nothing that currently works.

## Considered options

1. **OTEL-only** (chosen): remove `sentry-sdk`; errors are span exceptions + status, OTEL logs with trace correlation, and an alertable `outcome=error` metric.
2. **Hybrid**: OTEL owns traces/metrics/logs; keep `sentry-sdk` as an error-only sink (`traces_sample_rate=0.0`), moved to runtime deps. Best error-triage UX, but a second vendor SDK and account to maintain.
3. **OTEL → Sentry via Alloy fan-out**: rejected — span-event drop guts error tracking (see drivers).

## Decision outcome

Option 1. The API emits traces, metrics, and logs exclusively through OpenTelemetry to the configured OTLP endpoint (Alloy). `sentry-sdk`, its init code, and `SENTRY_DSN_API` config are removed. Custom domain spans/metrics (scan pipeline, ML client) and SQLAlchemy/Redis auto-instrumentation make the OTEL data rich enough to debug with.

Error triage happens in the OTLP backend (currently Grafana Cloud: Tempo span errors + Loki logs + Mimir alert rules on `tcgscan.scan.count{outcome="error"}`).

## Consequences

### Positive

- Single telemetry pipeline; backend swap (e.g. trialing New Relic) is an Alloy exporter change only.
- Sentry packaging bug (dev-only dep vs `--no-dev` image) disappears rather than needing a fix.
- Logs, traces, and metrics share resource attributes and trace context end to end.

### Negative

- No Sentry-grade issue grouping, source-context stack frames, or release health. If beta error volume makes triage painful, revisit option 2 (hybrid) — it layers back on without touching the OTEL code.
- `docs/TCG_Scan_Phase1.md` §12.8 and the beta-launch runbook referenced Sentry; the runbook is updated, the spec deviation is recorded here.
- `.cursor/commands.md` `/fix-from-sentry` and `/retro` templates reference Sentry and are stale until reworked against Grafana.

## Validation

- `apps/api` unit tests assert providers (tracer/meter/logger) initialize from `OTEL_EXPORTER_OTLP_ENDPOINT` alone and that no `sentry` import remains.
- Grep gate: no `sentry` references in `apps/api` source or Python dependency declarations.

## References

- Sentry OTLP limitations: https://docs.sentry.io/concepts/otlp/ (span events dropped; no OTLP metrics)
- `infra/alloy/config.alloy` — OTLP fan-out (metrics → Mimir, traces → Tempo, logs → Loki)
- `docs/TCG_Scan_Phase1.md` §12.8
