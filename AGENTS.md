# AGENTS.md — TCG Scan

> This file is the single source of truth for **any AI coding agent** (Cursor, Claude Code, Codex, Antigravity, etc.) working in this repository.
> It is read by Cursor 2.4 subagents, Claude Code, and any tool that follows the [AGENTS.md standard](https://agents.md).
> Per-package overrides live in `apps/<name>/AGENTS.md` and `packages/<name>/AGENTS.md` — agents walk hierarchically, so the **nearest** AGENTS.md wins for any file being edited.

---

## 0. Project context

**TCG Scan** is an AI-native price intelligence platform for trading cards (all major TCGs + sports). Users photograph a card and instantly see:
- last 30 days of sold comps across eBay, TCGPlayer, Cardmarket, and auction houses,
- current active listings,
- AI condition grade + grade-ladder ROI verdict,
- portfolio analytics, price alerts, and agentic insights.

**Direct competitors we are outbuilding**: 130point, Card Ladder, Market Movers, Slabfy, Ludex, Collectr, CardPriceIQ.
**Headline differentiator**: multi-TCG + sports + cross-marketplace + AI-native + agentic — none of the competitors do all five.

The canonical product spec is `docs/TCG_Scan_Phase1.md`. **Read it before doing anything non-trivial.** If the spec and this file disagree, the spec wins; raise the discrepancy in the PR description.

---

## 1. Architecture at a glance

Monorepo (`pnpm` + Turborepo):

```
tcg-scan/
├── apps/
│   ├── web/        Next.js 15 (App Router) + TypeScript + Tailwind + shadcn/ui
│   ├── api/        FastAPI (Python 3.12) + Pydantic v2 — the core HTTP API
│   ├── worker/     Temporal SDK (Python) — durable workflows for ingestion + alerts
│   └── ml/         Modal deployments — detect / embed / ocr / grade endpoints
├── packages/
│   ├── sdk-ts/     Auto-generated TypeScript client from apps/api OpenAPI
│   ├── sdk-py/     Internal Python client
│   ├── ui/         shadcn-based shared React components
│   ├── schema/     Shared Zod + Pydantic models (JSON Schema as source of truth)
│   └── agents/     LangGraph graphs (Python) + Claude prompt templates
├── infra/          Docker compose + Terraform + GitHub Actions workflows
├── data/           Catalog ETL scripts and dev seeds
└── docs/           ADRs, runbooks, the Phase 1 plan
```

**Tech stack — DO NOT swap without an ADR in `docs/adr/`.**

| Concern | Choice |
|---|---|
| Web framework | Next.js 15 App Router + TS |
| UI | Tailwind + shadcn/ui + lucide-react + Recharts |
| Backend | FastAPI + Pydantic v2 |
| OLTP | Postgres 16 (+ pgvector) — local Docker / Railway |
| Vector DB (images) | Qdrant |
| Cache / queue | Redis (Upstash or local) |
| Workflows | Temporal (Cloud or local compose; cron CLI also supported) |
| ML serving | Modal.com (GPU pay-per-second) — stubs until weights deployed |
| Object storage | Cloudflare R2 (planned; not required for local demo) |
| Auth | **Supabase Auth** (JWT). Clerk removed. |
| Payments | Stripe |
| Agents | LangGraph graphs (heuristics today; Claude when `ANTHROPIC_API_KEY` wired) |
| Observability | OpenTelemetry → Grafana Cloud, LangSmith, Sentry (hooks; keys pending) |
| Product brand | UI ships as **TCG Chart**; docs/package name **TCG Scan** |

---

## 2. Setup & common commands

### Bootstrap

```bash
# one-time
pnpm install
docker compose -f infra/docker/docker-compose.yml up -d   # postgres + qdrant + redis
uv sync                                                   # python deps for apps/api, apps/worker, apps/ml
pnpm db:migrate                                           # alembic
pnpm db:seed                                              # dev fixtures
```

### Day-to-day

```bash
pnpm dev                # turbo run dev — all apps in parallel
pnpm dev --filter web   # just one app
pnpm test               # unit + integration (turbo, cached)
pnpm lint               # eslint + ruff + mypy
pnpm typecheck          # tsc + mypy strict
pnpm build              # production builds
pnpm sdk:generate       # intended OpenAPI regen — currently a placeholder; sdk-ts is hand-maintained
pnpm eval               # apps/ml eval harness
pnpm db:demo            # migrate + seed + stub-embed catalogs into Qdrant
```

### Things that touch real services

Never run these without explicit user approval in the chat:
- `pnpm worker ingest:*` / `pnpm ingest:*` against production credentials
- `modal deploy` to the prod profile
- any `stripe` or `temporal` CLI command pointing at prod
- any DB migration on a non-local DB

---

## 3. Code conventions

### TypeScript (apps/web, packages/sdk-ts, packages/ui)

- Strict mode on. **No `any`** without a `// reason:` comment.
- Prefer **Server Components**; mark Client Components explicitly with `"use client"` only when needed (state, browser APIs).
- Data fetching: use `@tcgscan/sdk-ts` (Server Components and client). React Query is **not** wired yet — do not invent a second data layer without an ADR.
- Routing: App Router only. No `pages/` dir. Use route groups + parallel routes for shared layouts.
- Forms: prefer `react-hook-form` + Zod when adding complex forms. Shared Zod scaffolds live in `packages/schema` (still thin; API Pydantic remains source of truth for many DTOs).
- Errors: throw typed errors; never return error strings as data.
- Components: prefer composition over props soup; one component per file; co-locate tests as `*.test.tsx`.
- Styling: Tailwind utility classes; component variants via `cva` (class-variance-authority); design tokens via shadcn theme.
- Imports: absolute via `@/` (web) or `@tcgscan/<pkg>` (workspace). Sorted: stdlib → external → workspace → local. `eslint-plugin-import` enforces.
- Naming: `PascalCase` components, `camelCase` functions, `SCREAMING_SNAKE_CASE` env vars, `kebab-case` filenames.

### Python (apps/api, apps/worker, apps/ml, packages/agents, packages/sdk-py)

- Python 3.12. Managed by `uv`.
- Formatter: `ruff format`. Linter: `ruff check`. Type checker: `mypy --strict`.
- **Async-first**: FastAPI route handlers are `async def`. Use `asyncpg` / `httpx.AsyncClient`. No `requests` in app code. Prefer async DB access; `psycopg2-binary` may exist only for Alembic sync migrations.
- All function signatures fully type-hinted. Pydantic v2 models for all DTOs.
- Dependency injection via FastAPI `Depends()`. **No business logic in route handlers** — keep them thin; logic lives in `services/` modules.
- Errors: raise typed exceptions (`AppError`, `NotFoundError`, …). A global FastAPI exception handler maps them to RFC 9457 problem-json responses.
- Logging: `structlog` with JSON output. Never `print()`. Never log secrets, tokens, PII, or raw card images.
- Tests: `pytest` + `pytest-asyncio` + `pytest-anyio`. Aim for strong coverage on changed lines; CI does **not** currently enforce an 80% gate.
- DB access: SQLAlchemy 2.x async + Alembic migrations. Never raw SQL in route handlers; use repository modules.
- LLM calls: only through `packages/agents`. Never inline an Anthropic client in `apps/api` or `apps/web`.

### Shared schema (`packages/schema`)

- Target: JSON Schema as source of truth with Zod + Pydantic codegen.
- Today: thin scaffolds; `pnpm schema:build` emits stub Zod. Most DTOs still live in `apps/api` Pydantic models and hand-written `packages/sdk-ts`.
- Breaking schema changes that affect the public API require an ADR in `docs/adr/`.

---

## 4. Per-app guidance (overrides for `apps/<name>/AGENTS.md`)

### `apps/web`

- Server Component by default. Pages under `app/(public)/...` are SEO-targeted (no auth gate).
- `/card/[slug]` MUST be statically generatable + ISR (`revalidate: 900`). No client-side waterfalls — preload everything in the Server Component.
- Use `next/image` for all `<img>`. Card images come from R2 via a signed URL helper.
- Camera capture: use `getUserMedia`; fallback to `<input type="file" capture="environment">` on browsers without `getUserMedia`.
- Mobile breakpoint is `sm`. Design mobile-first.
- Analytics: `@vercel/analytics` + PostHog (when env present). Never block UI on analytics.

### `apps/api`

- One FastAPI app, mounted at `/v1`. **Version everything.**
- Endpoints: thin handlers → services → repositories → DB.
- Auth: Supabase JWT verified in `AuthMiddleware` → `request.state.user`. Protected handlers call `resolve_db_user` (opt-in). Public routes simply omit that call — there is no `@public_route` decorator today.
- Rate limiting: Redis counters for scans / search IP limits. Free tier limits enforced here; web shows soft upgrade copy only.
- Cache: Redis used for market/card caches and rate limits where wired.
- Prefer short request handlers. Long ingest work belongs in the Temporal worker / CLI — not blocking the API. (A future jobs/SSE pattern is optional; not implemented yet.)

### `apps/worker`

- Temporal worker; activities are pure Python functions, workflows are deterministic.
- Activities: idempotent. Retries are automatic — design for at-least-once execution.
- Schedules:
  - `ebay_active`: top-1k popular cards every 15 min, long tail every 6h.
  - `ebay_sold`: hourly top-10k, daily everything else.
  - `tcgplayer` / `cardmarket`: daily.
  - `catalog_refresh`: weekly + on-demand.
  - `digest_agent`: daily 06:00 user-local.
- Heartbeats every ≤ 30 s for long activities. Use Temporal's `activity.heartbeat()`.
- Secrets via env. **Never** hardcode API keys, never log them.

### `apps/ml`

- Each Modal endpoint is a separate function in a single `app.py` per model.
- Public contract: stable JSON in `apps/ml/contracts.md`. Update the contract file in the same PR as the code change.
- GPU autoscale: `min_containers=0`, `max_containers=10` for v1. Use `gpu="T4"` unless docs say otherwise.
- Model weights live in Modal volumes, not in git. Version weights with a manifest in `apps/ml/weights/manifest.toml`.
- Cold start budget: < 8 s. If you can't hit it, document why in the PR.
- Every endpoint emits OpenTelemetry spans + a `tcgscan.ml.<model>.latency_ms` metric.

### `packages/agents`

- Every agent = one LangGraph graph under `packages/agents/tcgscan_agents/<agent_name>/` + typed I/O + prompts.
- Graphs today (scan, pricing, grade_roi, monitor, digest) are mostly **rules / internal API wrappers**; Claude escalation is the intended next step when `ANTHROPIC_API_KEY` is wired — do not claim LLM behaviour that is not in code.
- **Hard token + cost budget per node**: `BudgetGuard(...)`. Exceed → raise + halt graph.
- Tracing: `@traced(...)` (structlog today; LangSmith when keys present).
- Tools live in `packages/agents/tcgscan_agents/tools/` and are reused — never inline marketplace HTTP in the API.
- When a node gains real LLM I/O, add golden snapshots under `tests/golden/`.

---

## 5. Data & ingestion rules

- Every external request goes through `packages/agents/tools/<source>.py` or `apps/worker/sources/<source>.py` — **never** raw `httpx.get` in route handlers.
- Respect every API's rate limit. Wrap clients with `tenacity` + token-bucket; document the limit in the source file.
- Scraping fallback (eBay completed listings, Cardmarket trends, auction houses): allowed only where ToS permits and a `LEGAL.md` note exists. Cache aggressively.
- Normalise every comp into `sale_event` with `(source, sold_at, price, currency, grade_company, grade, condition, listing_url, raw_payload jsonb)`.
- Currency: store in source currency + USD-normalised at sale time using `fx_rate` table; display per user locale.
- **Never store user-uploaded card images longer than 30 days** unless the user opted in (privacy posture).

---

## 6. AI/ML rules

- Card-ID model changes: PR MUST run the eval harness (`pnpm eval`) and post the report. Top-1 regression > 1pp blocks merge unless explicitly waived.
- Condition-grader changes: report MAE per grade bucket. Regression > 0.3 grades blocks merge.
- Embeddings: keep dim = 1024. If you change it, you re-embed the entire catalog — coordinate via an ADR.
- Augmentation pipeline lives in `apps/ml/augment/`. Add a fixed-seed test before changing it.
- **Active learning loop**: low-confidence scans + user corrections feed `data/labels/inbox/` for next training cycle. Never auto-train; require explicit run.

---

## 7. Testing & quality gates

**CI today (enforced):** `pnpm lint` + `pnpm typecheck` + `pnpm test` (Turbo), plus Python `ruff` / `mypy` / `pytest` on api, worker, ml, agents, sdk-py. See `.github/workflows/ci.yml`.

**Not enforced yet (targets):** coverage %, Playwright e2e under `apps/web/e2e/`, docker-compose `@integration` suite, ML eval on every ML PR, OpenAPI↔sdk-ts drift checks.

- Prefer unit tests next to changed modules; expand integration/e2e as you touch those surfaces.
- CI is the source of truth — don't merge red. If CI is flaky, file an issue + fix; don't `git push -f`.

### Definition of Done (every PR)

- [ ] Lint, typecheck, tests green
- [ ] New code has tests for the behaviour you changed
- [ ] If public API shapes changed: update `packages/sdk-ts` (hand-maintained until codegen) and `apps/api/docs/endpoints.md`
- [ ] If user-facing: screenshots / Loom in the PR when UI changes meaningfully
- [ ] If perf-sensitive: latency numbers in the PR
- [ ] If ML-touching: run `pnpm eval` and note results when fixtures exist
- [ ] CHANGELOG entry under "Unreleased"

---

## 8. Cursor / Claude Code subagent guidance

This repo is designed for **agentic coding**. When working in Cursor 2.4 or Claude Code:

### When to spawn subagents

Spawn a subagent (max 3 in parallel — Cursor 2.4 starts to step on its own toes above that) when:
- A task naturally splits across `apps/web` + `apps/api` + `packages/sdk-ts` (one agent per app).
- You are writing tests in parallel with implementation (one writes code, one writes tests).
- You are running a long-running task (eval, full lint sweep) and want to keep coding.

### When NOT to spawn subagents

- Single-file changes
- Bug fixes inside one module
- Anything where the subagents would edit overlapping files

### Subagent handoff format

Each subagent task spec MUST include:
1. **Goal** — one sentence.
2. **Files in scope** — explicit list; agent must not edit outside these.
3. **Inputs** — schemas, fixtures, or upstream PR context.
4. **Acceptance criteria** — concrete tests / metrics.
5. **Out of scope** — what the parent agent will handle.

### Slash commands

See `.cursor/commands.md` for reusable command templates (`/scaffold-endpoint`, `/add-card-game`, `/new-agent`, `/run-eval`, etc.).

---

## 9. Security & privacy

- Secrets in Vercel / Railway / Modal / Temporal / Supabase / Stripe dashboards — never in git, never in logs.
- All inbound requests: input validation via Pydantic / Zod. Reject unknown fields.
- All outbound HTTP: timeouts, retries with jitter; prefer circuit breakers on worker clients (`ResilientClient`).
- PII: user emails, IPs, card photos. Don't ship PII to LLMs unless the user is in scope and we have consent.
- Stripe webhooks: verify signatures. Replay-safe (idempotency keys).
- Auth: never trust a client-claimed user id; always verify the Supabase JWT (or reject). Dev header auth is forbidden when `ENVIRONMENT=production`.
- Dependency hygiene: run `pnpm audit` + `uv pip audit` regularly. CVEs ≥ 7.0 should block merges to main.

---

## 10. Things never to do (hard rules)

- ❌ Inline an Anthropic / OpenAI API key, or any other secret, in code.
- ❌ Use `psycopg2` / `requests` (sync) — async only.
- ❌ Add a new database. Use Postgres + Qdrant + Redis. No Mongo, no DynamoDB.
- ❌ Add a new vector DB. Qdrant only.
- ❌ Add a new LLM provider without an ADR. Claude only for v1.
- ❌ Call a marketplace API directly from `apps/web` — always via `apps/api`.
- ❌ Store card images in Postgres. R2 only; reference by signed URL.
- ❌ Ship un-traced LLM calls. Every call goes through `packages/agents`.
- ❌ Use `localStorage` for anything other than user UI preferences (theme, last filter).
- ❌ `git push --force` on `main`. Use `--force-with-lease` only on your own feature branches.

---

## 11. When stuck

1. Re-read `docs/TCG_Scan_Phase1.md` for product intent.
2. Search `docs/adr/` for a decision on the question.
3. Look at the closest existing pattern in the repo and follow it.
4. If still stuck, leave a `TODO(agent):` comment + open a draft PR with a clear question — do not invent a new pattern.

---

## 12. Appendix — env vars

The full list lives in `.env.example`. Highlights every agent must respect:

| Var | Used by | Notes |
|---|---|---|
| `DATABASE_URL` | api, worker | Postgres, async driver |
| `QDRANT_URL` / `QDRANT_API_KEY` | api, worker, ml | Qdrant Cloud or local |
| `REDIS_URL` | api, worker | Upstash |
| `R2_BUCKET` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` | api, worker | Cloudflare R2 (optional for local) |
| `SUPABASE_URL` / `SUPABASE_JWT_SECRET` or `SUPABASE_JWKS_URL` | api | JWT verify (required in production) |
| `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` | web | Browser/SSR Supabase client |
| `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` / `STRIPE_PRO_PRICE_ID` | api | Billing |
| `ANTHROPIC_API_KEY` | agents | LLM access when agents escalate to Claude |
| `MODAL_*_URL` / `MODAL_TOKEN_*` | api, ml | ML endpoints + deploy |
| `TEMPORAL_ADDRESS` / `TEMPORAL_NAMESPACE` | worker | Local or Temporal Cloud |
| `EBAY_APP_ID` / `EBAY_CERT_ID` or `EBAY_OAUTH_TOKEN` | worker, api | Browse API |
| `EBAY_INSIGHTS_TOKEN` | worker | True sold comps (optional) |
| `EBAY_AFFILIATE_TRACKING_ID` / `EBAY_AFFILIATE_CAMPAIGN_ID` | api | EPN link rewriting |
| `TCG_API_KEY` | worker | tcgapi.dev |
| `APIFY_TOKEN` | worker | Cardmarket dataset |
| `DEV_AUTH_ENABLED` | api, web SDK | Local bypass via `X-Dev-User-Id` |
| `LANGSMITH_API_KEY` / `LANGSMITH_PROJECT` | agents | Observability |
| `SENTRY_DSN_<APP>` | all | One per app |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | all | Grafana Cloud |

---

*End of root AGENTS.md. Per-package AGENTS.md files override anything here for files inside their directory.*
