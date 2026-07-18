# SRE — Log Signal Quality, Verification, and (later) SLI/SLO Wiring

> Status: **Phase 1 in progress** (fix signals). Phases 2–4 (verify → SLI/SLO → dashboards/alerts via Terraform) are
> blocked on Phase 1 landing and being verified. This file is the working reference for all of it.
>
> Related: `docs/adr/0001-otel-only-observability.md` (OTEL-only decision), `infra/alloy/config.alloy` (OTLP → Grafana
> Cloud fan-out), branch `19-better-telemetry-for-api` (custom spans/metrics + OTLP logs export).

## 1. Audit summary (2026-07-18)

Three parallel read-only audits covered `apps/api`, `apps/worker` + `apps/ml`, and `packages/agents` + `packages/sdk-py`.

**Headline: the codebase contains zero intentional `log.error` call sites.** Nothing can page on level today.

| Area | debug | info | warning | error | exception/critical | print() |
|---|---:|---:|---:|---:|---:|---:|
| apps/api | 5 | 12 | 32 | 0 | 6 | 0 |
| apps/worker | 3 | 19 | 9 | 0 | 0 | 9 |
| apps/ml | 0 | 0 | 0 | 0 | 0 | 1 |
| packages/agents + sdk-py | 0 | 2 | 0 | 0 | 0 | 0 |

Systemic patterns found:

1. **Failures demoted one level.** Final failures live at WARNING (ML outage → stub, Qdrant down, ingest job failures,
   Temporal connect failure), degradation lives at DEBUG (Redis cache failures — never exported: root logger is INFO),
   and ~20 failure paths are fully silent (`except: pass`), including rate limiting **failing open**.
2. **Retry pattern violated everywhere.** Target: attempt = WARNING with attempt numbers; exhaustion = ERROR. The two
   real retry clients (`apps/worker/tcgscan_worker/http.py` ResilientClient, `apps/api/tcgscan_api/sources/http_client.py`)
   log respectively "WARNING without attempt context, silent exhaustion, silent circuit breaker" and "nothing at all".
3. **WARNING/INFO diluted by per-item chatter.** Per-card logs inside batch loops that run at 10k cards/hour; `@traced`
   emits 2 INFO per graph node — and logs success-style `agent.node.end` even when the node raised.
4. **Data-corrupting fallbacks are quiet.** Missing FX rate logs WARNING and returns the unconverted amount into
   `sale_event.price_usd`; failed embeds silently substitute stub vectors into Qdrant.

## 2. Severity playbook (the contract for all fixes)

| Level | Meaning | Examples |
|---|---|---|
| **ERROR** | Pages a human. | Final failure after retries; failed job/batch/activity run; circuit breaker opens; data-corrupting fallback (missing FX rate); 5xx from our own bug/config; worker cannot connect. |
| **WARNING** | Degraded but handled; actionable if recurring. | Individual retry attempt (with `attempt`/`max_attempts`); fallback to stub/heuristic; rate-limit fail-open; invalid Stripe signature; BudgetGuard halt; corrupt cache payload. |
| **INFO** | State changes + run summaries with counts. | Job/batch start+done with `{success, failed, empty}` counters; startup config; alert triggered. **Never per-item inside a loop.** |
| **DEBUG** | Per-item detail; expected empties; node start/end. | Not exported (root level INFO) — nothing operationally relevant may hide here. |

Companion rules:
- A caught exception that changes behaviour (fallback/skip/empty result) **must log** — never silently `pass`.
- Structured key-values only (`log.warning("evt", key=val)`), no printf-style, no `print()` outside CLI help text.
- Never log secrets, tokens (`eias_token`), raw emails, image payloads, or signed URLs.
- **Phase 1 changes log signals only** — no behaviour changes except where explicitly listed (worker exit code).

## 3. Work packages (Phase 1)

Each package has a strictly disjoint file scope; owners are parallel subagents. No package touches shared files
(`conftest.py`, `pyproject.toml`, `uv.lock`, `CHANGELOG.md`, this file).

| # | Package | Files | Key fixes |
|---|---|---|---|
| A1 | api ML client | `apps/api/.../services/ml_client.py` | ERROR on fallback (URL set, call failed); stub mode stays quiet |
| A2 | api scan | `apps/api/.../services/scan.py` | Qdrant-down → ERROR; corrupt-cache pass → WARNING; verdict except split expected/unexpected |
| A3 | api Redis | `apps/api/.../middleware/rate_limit.py`, `services/cache.py` | Fail-open → WARNING; cache get/set failures DEBUG → WARNING (rename `cache.miss`-on-error → `cache.get_failed`) |
| A4 | api ingest jobs | `services/catalogue_import.py`, `services/catalogue_ingest.py`, `services/ebay_ingest.py` | Job failure WARNING → ERROR |
| A5 | api retry client | `apps/api/.../sources/http_client.py` | Attempt WARNING w/ numbers; exhaustion ERROR |
| A6 | api billing+errors | `services/billing.py`, `main.py` | Stripe signature WARNING; missing user_id WARNING; AppError handler logs ERROR for ≥500; CORS log structured |
| A7 | api misc+PII | `sources/one_piece.py`, `repositories/admin.py`, `repositories/users.py`, `services/source_audit.py`, `services/ebay_account_deletion.py` | Level fixes; redact `eias_token`; hash/drop emails |
| W1 | worker retry client | `apps/worker/.../http.py` | Attempt WARNING w/ numbers; exhaustion ERROR; circuit open ERROR (transition) + reject DEBUG |
| W2 | worker pricing | `pricing/ingest.py`, `pricing/fx.py` | Per-card empty/success → DEBUG; batch summary INFO with counters; `partial_failure` ERROR when failed>0; FX missing rate → ERROR (behaviour unchanged); prints → structlog |
| W3 | worker runtime | `worker.py`, `workflows/activities.py`, `schedules.py`, `rollup.py`, `catalog/runner.py` | Connect fail → ERROR + exit 1; activity boundary INFO logs; unknown-game ERROR; prints → structlog |
| W4 | worker sources | `embedding.py`, `sources/ebay_auth.py`, `sources/ebay_active.py`, `sources/tcgplayer.py`, `sources/cardmarket.py`, `sources/psa_pop.py`, `digest/runner.py` | Embed degradation counters + threshold ERROR; OAuth failure ERROR; silent sources get DEBUG summaries; per-spec/per-user → DEBUG; drop digest body from logs |
| M1 | ml logging | `apps/ml/tcgscan_ml/app.py`, `grade/heuristic.py` | structlog request/error logging; degraded-grade WARNING |
| G1 | agents tracing+budget | `packages/agents/.../tracing.py`, `budget.py` | @traced: DEBUG start/end + status/duration, ERROR on raise, no success-log on failure; BudgetGuard WARNING before raise |
| G2 | agents tools+graphs | `tools/pricing.py`, `grade_roi_agent/graph.py`, `scan_agent/graph.py`, `packages/sdk-py/.../client.py` | Non-200/HTTP errors → WARNING with context (fixes monitor false negatives); stub path DEBUG; sdk-py failure logging |

## 4. Verification plan (Phase 2 — before any Terraform/dashboards)

1. **Unit-level:** every package above lands tests asserting event names + levels (`structlog.testing.capture_logs`).
   Full suites green: `apps/api`, `apps/worker`, `packages/agents` (`uv run pytest`), plus `ruff` + `mypy --strict`.
2. **Local pipeline smoke:** run `docker compose --profile observability up` (Alloy) + API with
   `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318`, then force each failure class and confirm the log line arrives
   in Loki at the right level with `trace_id` attached:
   - stop Redis → expect `cache.get_failed` / `rate_limit.fail_open` WARNING;
   - stop Qdrant → expect `scan.qdrant_unavailable` ERROR (+ span error);
   - set a bogus `MODAL_DETECT_URL` → expect `ml.error` ERROR with `mode=fallback`;
   - run `pricing` ingest against an unreachable source → retry WARNINGs with attempt numbers, then exhaustion ERROR.
3. **Signal review:** 24h of local/dev traffic; confirm ERROR volume ≈ 0 in steady state (no alert fatigue), WARNING is
   low and meaningful, INFO is summaries only. Adjust levels that misfire **before** wiring alerts.

## 5. Later phases (reference material — do not build yet)

**Phase 3 — SLIs/SLOs** (candidates, from the metrics on `19-better-telemetry-for-api`):

| SLI | Source | Draft SLO |
|---|---|---|
| Scan success rate | `tcgscan.scan.count{outcome}` | ≥ 99% ok+cache_hit |
| Scan p95 latency | `tcgscan.scan.duration` | < 2.5s (Phase-1 KPI §9) |
| ML live-mode rate | `tcgscan.ml.requests{mode}` | fallback < 1% when URLs configured |
| Ingest batch health | `pricing.batch.*` events / future counter | 0 partial-failure ERRORs per day |
| Cache availability | `cache.get_failed` WARNING rate | < 0.1% of requests |
| API availability | FastAPI HTTP metrics (5xx ratio) | ≥ 99.5% |

**Phase 4 — dashboards + alert conditions** (Terraform against Grafana Cloud): alert on any ERROR-level Loki line per
service (`{service_name="tcgscan-api"} | json | level="error"`), plus metric alerts on the SLOs above. One dashboard
per service + one scan-funnel dashboard. Keep alert rules in `infra/terraform/` (does not exist yet).

## 6. Status log

- 2026-07-18: Audit completed (3 subagents). Phase 1 fan-out launched (14 packages). OTEL traces/metrics/logs export
  and Sentry removal already landed on `19-better-telemetry-for-api` (commit `2b8c075`).
- 2026-07-18 (later): **Phase 1 complete.** All 14 packages landed and verified — full suites green:
  api (ruff/mypy/178 tests), worker (28), agents (11), ml (11). Deviations from plan:
  - **sdk-py skipped** (G2): structlog is not declared in `packages/sdk-py/pyproject.toml`; adding logging there needs
    a dependency change — deferred (small P1 follow-up).
  - **`psa_pop.done` run summary skipped** (W4): no batch runner exists in that module; per-spec logs demoted to DEBUG.
  - **`test_worker.py` scaffold test** rewritten to assert the sanctioned behaviour change (connect failure →
    `SystemExit(1)`).
  - Key new alertable events: `ml.error` (ERROR), `scan.qdrant_unavailable` (ERROR), `scan.verdict_failed`,
    `catalogue_import.failed` / `catalogue_ingest.failed` / `ebay_ingest.failed` (ERROR), `source_http.exhausted`,
    `http.exhausted`, `http.circuit_open`, `pricing.batch.partial_failure`, `fx.missing_rate` (ERROR),
    `embed.run.degraded`, `worker.connect_failed`, `api.app_error` (5xx), `agent.node.failed`, `ebay.auth_failed`,
    `catalog.unknown_game`, and `*.failed` on all four ML endpoints.
  - Key WARNING events for recurrence review: `rate_limit.fail_open`, `cache.get_failed` / `cache.set_failed` /
    `cache.payload_invalid`, `scan.cache_payload_invalid`, `source_http.retry` / `http.retry` (with attempt numbers),
    `stripe.webhook_signature_invalid` / `stripe.webhook_unresolved_user`, `agent.budget_exceeded`,
    `tool.pricing.*_failed`, `grade_roi.comps_fetch_failed`, `grade.image_unreadable`, `source_audit.check_failed`.
  - **Next: Phase 2 verification (§4)** — the local Alloy→Loki smoke test forcing each failure class, then the 24h
    signal review, before any Terraform/dashboards/alerts.
