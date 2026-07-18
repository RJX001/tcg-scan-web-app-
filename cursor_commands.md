# .cursor/commands.md — TCG Scan Slash Commands

> Drop this at `.cursor/commands.md` in the repo root (Cursor 2.4+ picks it up automatically).
> Each command below is a reusable prompt template you can invoke in Cursor's chat with `/command-name`.
> They are tuned to the TCG Scan monorepo as defined in `AGENTS.md` and `docs/TCG_Scan_Phase1.md`.
> When you invoke one, replace `${...}` placeholders before sending. Each command tells the agent which AGENTS.md to read first and what acceptance criteria look like.

---

## /bootstrap

Bootstrap the monorepo from scratch. Idempotent — safe to re-run.

```
Read AGENTS.md and docs/TCG_Scan_Phase1.md §3 (Architecture) and §12.2.

Initialise the Turborepo monorepo:
- Root: pnpm-workspace.yaml, turbo.json, .nvmrc (node 20), .python-version (3.12), .editorconfig, .gitignore, LICENSE (MIT).
- apps/web — Next.js 15 App Router + TS + Tailwind + shadcn/ui + ESLint + Vitest (Playwright e2e is a target, not required for bootstrap).
- apps/api — FastAPI + Pydantic v2 + uv-managed + ruff + mypy --strict + pytest + pytest-asyncio.
- apps/worker — Temporal Python SDK skeleton + ruff + mypy + pytest.
- apps/ml — Modal stub with app.py per model (detect, embed, ocr, grade) and a contracts.md.
- packages/sdk-ts — generated client placeholder + openapi-typescript script.
- packages/sdk-py — internal client placeholder.
- packages/ui — shadcn component library with Button, Card, Dialog, Input, Tooltip, Toast.
- packages/schema — JSON Schema files + Zod + Pydantic generators wired via `pnpm schema:build`.
- packages/agents — LangGraph skeleton, BudgetGuard utility, tools/ folder, tracing decorator.
- infra/docker/docker-compose.yml — postgres-16 (+pgvector), qdrant, redis, temporalite.
- infra/github/ — reusable workflows for lint, test, build, sdk-generate, eval.
- .cursor/commands.md (this file), AGENTS.md (root), CLAUDE.md (mirror of §3 of the plan), per-package AGENTS.md.
- .env.example with every variable listed in AGENTS.md §12.

Acceptance:
- `pnpm install && pnpm lint && pnpm typecheck && pnpm test` passes on a fresh clone.
- `docker compose up -d` brings up postgres/qdrant/redis healthy.
- `pnpm dev --filter web` serves localhost:3000 with a placeholder landing page.

Do NOT add product code — scaffolding only. Open a PR titled "chore: bootstrap monorepo".
```

---

## /scaffold-endpoint

Scaffold a new FastAPI endpoint end-to-end (route → service → repo → tests → SDK regen).

```
Read apps/api/AGENTS.md and packages/schema/AGENTS.md.

Add a new endpoint to apps/api:

- Method + path: ${METHOD} ${PATH}                  (e.g. GET /v1/cards/{id}/comps)
- Purpose: ${ONE_SENTENCE_PURPOSE}
- Request schema: ${REQUEST_SCHEMA}                 (or "none" for GET)
- Response schema: ${RESPONSE_SCHEMA}
- Auth: ${PUBLIC|AUTHED|PRO_TIER}
- Cache: ${NONE|REDIS_KEY_TEMPLATE_WITH_TTL}
- Rate limit: ${TIER_OR_OVERRIDE}

Generate:
1. JSON Schema in packages/schema; run `pnpm schema:build`.
2. Route handler in apps/api/routes/${MODULE}.py — thin, async.
3. Service in apps/api/services/${MODULE}.py — business logic.
4. Repository in apps/api/repositories/${MODULE}.py — DB access.
5. Pytest in apps/api/tests/${MODULE}_test.py — happy + 2 edge cases.
6. Integration test under @integration tag if it touches DB or external services.
7. Update OpenAPI; run `pnpm sdk:generate`.
8. Add a row to apps/api/docs/endpoints.md.

Acceptance:
- Tests green, types pass, p95 latency < 200ms in local benchmark (state if N/A).
- No business logic in the route handler.
```

---

## /add-card-game

Add a new TCG / sports category end-to-end.

```
Read apps/worker/AGENTS.md, packages/schema/AGENTS.md, and docs/TCG_Scan_Phase1.md §4.1.

Add support for: ${GAME_NAME}
- Catalog source: ${URL_OR_API}
- Auth required? ${YES|NO}
- Estimated card count: ${N}
- Image source: ${URL_OR_NOTE}

Deliver:
1. Catalog ingester at apps/worker/catalog/${slug}.py — async, idempotent, paginated.
2. Mapping module that normalises source fields to card_identity schema (packages/schema/card_identity.json).
3. CLI hook: `pnpm worker ingest:catalog --game ${slug}` works locally.
4. Tests with a recorded fixture (pytest-httpx VCR-style).
5. Add an embedding job to enqueue image embeddings for the new cards into Qdrant collection `cards`.
6. Update docs/data-sources.md with the new source, rate limit, and any ToS notes.
7. Add the game to the `game` enum migration; create the Alembic revision.

Acceptance:
- Ingester runs end-to-end against a local fixture and inserts ≥ 50 cards.
- Embedding job successfully writes to Qdrant.
- Top-1 scan accuracy on 20 hand-shot test photos ≥ 80% (run `pnpm eval --game ${slug}`).
```

---

## /new-agent

Add a new LangGraph subagent in packages/agents.

```
Read packages/agents/AGENTS.md and docs/TCG_Scan_Phase1.md §6.

New agent: ${AGENT_NAME}
- Purpose: ${ONE_SENTENCE}
- Trigger: ${HOW_IT_IS_INVOKED}
- Inputs (Pydantic): ${SCHEMA}
- Outputs (Pydantic): ${SCHEMA}
- Tools needed: ${LIST}
- Default LLM: claude-haiku-4-5-20251001
- Escalation? ${NO|"YES — node X uses claude-sonnet-4-6 for synthesis"}
- Cost ceiling: ${MAX_USD_PER_RUN}

Deliver:
1. packages/agents/${agent_name}/graph.py — LangGraph state machine.
2. packages/agents/${agent_name}/prompts.py — versioned prompt strings with docstrings.
3. packages/agents/${agent_name}/models.py — input/output Pydantic.
4. BudgetGuard wired into every node.
5. @traced decorator on every node — LangSmith project tcg-scan-{env}.
6. Golden tests in packages/agents/${agent_name}/tests/golden/ (snapshot 3 representative runs).
7. Unit tests for each node with mocked Claude.
8. Add the agent to packages/agents/__init__.py registry.
9. Wire into apps/api or apps/worker per the trigger spec.

Acceptance:
- Golden tests pass; LangSmith traces visible locally.
- Per-run cost < ceiling in 10-run benchmark.
- No PII in prompts.
```

---

## /add-price-source

Wire up a new price/comp source.

```
Read apps/worker/AGENTS.md §5 and docs/TCG_Scan_Phase1.md §4.2.

Source: ${NAME} (${URL})
Type: ${OFFICIAL_API | SCRAPER | THIRD_PARTY_API}
Auth: ${API_KEY_NAME or "none"}
Rate limit: ${REQ_PER_SEC}
ToS notes: ${SUMMARY + LINK}

Deliver:
1. Client wrapper at apps/worker/sources/${slug}.py with tenacity retries + token bucket + circuit breaker.
2. Normaliser mapping source → sale_event schema.
3. Temporal activity + workflow at apps/worker/workflows/${slug}_workflow.py with the schedule from §4.3 of the plan.
4. Provider interface compliance — pluggable via apps/worker/sources/registry.py.
5. Tests with fixtures; no live calls in CI.
6. Documentation in docs/data-sources.md (limits, schedule, fallbacks).
7. Add env vars to .env.example and AGENTS.md §12.

Acceptance:
- 500 sample comps end up in sale_event with all required fields.
- Daily roll-up job picks them up.
- LangSmith / Grafana dashboards show the new source.
```

---

## /implement-scan-pipeline

Stand up or extend the AI scan pipeline.

```
Read apps/ml/AGENTS.md, packages/agents/AGENTS.md, and docs/TCG_Scan_Phase1.md §5.

Target latency: p95 < 2.5s end-to-end on web.

Stages to (re)implement: ${ALL | LIST}
- detect: YOLOv11-nano, axis-aligned + rotated bbox, T4 GPU
- embed: DINOv2-base (or SigLIP-2) fine-tuned, 1024-dim, L2-normalised
- ann_search: Qdrant collection `cards`, top-20 with game filter
- ocr: PaddleOCR server mode
- rerank: joint score (cos-sim × OCR-match × popularity prior)
- grade: ResNet50 multi-head (centering, corners, edges, surface, overall)

Deliver:
1. Modal endpoint per stage in apps/ml/app.py with stable JSON contract documented in apps/ml/contracts.md.
2. Orchestrator: apps/api/services/scan.py composes the stages via async fan-out where possible.
3. FastAPI endpoint POST /v1/scan returning top-K matches with confidence + condition estimate.
4. Redis cache of embeddings by SHA-256 of canonicalised image bytes.
5. Eval harness extension in apps/ml/eval/ — top-1, top-5, MAE on grade, p50/p95 latency.
6. Frontend integration: apps/web/app/scan/page.tsx wired to /v1/scan via SDK.

Acceptance:
- `pnpm eval` reports top-1 ≥ 90%, top-5 ≥ 98% on the held-out set (or documents why below threshold).
- Cold start < 8s on Modal; warm p95 < 2.5s.
- LangSmith trace shows each stage with timings.
```

---

## /run-eval

Run the full ML / agent evaluation suite and post a report.

```
Read apps/ml/eval/README.md.

Execute:
1. `pnpm eval --suite full` (top-1, top-5, condition MAE, latency).
2. `pnpm test --filter agents -- --update-golden=false` (golden snapshot diffs).
3. Aggregate into a markdown report at apps/ml/eval/reports/${TIMESTAMP}.md with:
   - Per-game accuracy table.
   - Latency p50/p95 per stage.
   - Cost per scan (LLM + GPU seconds).
   - Diff vs the previous report.
4. Post the report as a PR comment (or paste in chat if no PR).

If any metric regressed beyond the threshold in AGENTS.md §6, mark the PR as DO NOT MERGE and surface the offending diff.
```

---

## /fix-from-sentry

Triage and fix a production error from Sentry.

```
Read AGENTS.md §7 and §9.

Sentry issue URL: ${URL}

Steps:
1. Read the error, the stack trace, and the breadcrumbs.
2. Identify the affected app (web / api / worker / ml) and load its AGENTS.md.
3. Reproduce locally with a minimal failing test (the fix MUST come with a test that fails without the fix).
4. Implement the fix. Keep the change minimal — no incidental refactors.
5. Add a CHANGELOG line under "Unreleased — Fixed".
6. Open a PR titled "fix(${scope}): ${short summary}" linking the Sentry issue.

If the error indicates a systemic issue (5+ occurrences in 24h or affecting > 1% of users), spawn a sub-agent to write a runbook entry at docs/runbooks/${slug}.md describing detection and rollback.
```

---

## /ship-ready

Pre-merge readiness check.

```
Run the Definition-of-Done checklist from AGENTS.md §7 against the current branch.

For each unchecked item, EITHER:
- check it off by actually doing it (run lint, regenerate SDKs, take screenshots, run eval, write the CHANGELOG entry), OR
- raise a "blocker" comment explaining why it cannot be done in this PR.

Output the final checklist as a markdown block I can paste into the PR description.
```

---

## /adr

Open a new architecture decision record.

```
Read docs/adr/_template.md.

Question: ${ONE_LINE_QUESTION}
Context: ${WHY_NOW}
Options being considered: ${LIST_2_TO_4}
My current lean: ${OPTION_OR_NONE}

Create docs/adr/${YYYY-MM-DD}-${slug}.md following the template:
- Context, Decision drivers, Considered options, Decision outcome, Consequences (positive + negative), Validation, References.
- Mark Status as Proposed.

Then post in chat a 5-bullet summary so I can decide before this gets merged.
```

---

## /onboard-me

Refresh my context after time away from the repo.

```
Read AGENTS.md and docs/TCG_Scan_Phase1.md, then:

1. Summarise the architecture in < 200 words.
2. List every workflow in apps/worker with its schedule.
3. List every LangGraph agent with its purpose and which LLM it uses.
4. List open ADRs and any "Proposed" status decisions.
5. Show the last 10 commits and group them by scope.
6. Highlight any TODO(agent) comments older than 14 days.

Output as a single chat reply. No code changes.
```

---

## /retro

Spin up a quick weekly retro doc seeded from git + Sentry + LangSmith.

```
Generate docs/retros/${YYYY-WW}.md with:
- Shipped this week (commits, PRs merged, grouped by scope).
- Production incidents (top 5 Sentry issues by frequency).
- Agent cost + accuracy (LangSmith dashboard summary).
- Roadmap delta vs docs/TCG_Scan_Phase1.md §8.
- 3 prioritised actions for next week.

Reuse the template at docs/retros/_template.md.
```

---

*End of command catalogue. Add new commands by appending an `## /name` section — Cursor 2.4+ picks them up on the next chat.*
