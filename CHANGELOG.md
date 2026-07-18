# Changelog

## Unreleased

### Added

- Log signal quality pass across api/worker/ml/agents (`sre.md`): first ERROR-level events for alertable failures (ML outage, Qdrant down, ingest job failures, retry exhaustion, circuit-breaker open, FX missing rate, embed degradation, worker connect failure, 5xx AppErrors, agent node failures); canonical retry logging (attempt WARNING with numbers → exhaustion ERROR) in both HTTP retry clients; Redis cache/rate-limit fail-open now visible at WARNING; per-item batch chatter demoted to DEBUG behind summary INFO counters; PII/token redaction (emails, `eias_token`, digest bodies, signed image URLs); worker exits non-zero when Temporal is unreachable
- API observability, fully OTEL-native: custom scan-pipeline spans (`scan.run` + detect/embed_ocr_grade/ann_search/rerank/verdict stages) and ML client spans with stub/fallback/live mode, business metrics (`tcgscan.scan.duration`, `tcgscan.scan.stage.duration`, `tcgscan.scan.count`, `tcgscan.ml.requests`), SQLAlchemy + Redis auto-instrumentation, OTLP log export with structlog JSON output + trace correlation, and standard `OTEL_TRACES_SAMPLER` env-var support

### Removed

- Sentry (`sentry-sdk`, init code, `SENTRY_DSN_API`): never loaded in production (dev-only dep vs `--no-dev` image) and superseded by the OTEL-only pipeline — see `docs/adr/0001-otel-only-observability.md`

- Monorepo bootstrap (Turborepo, apps, packages, infra)
- Weeks 1–5: catalog ingest (Pokemon, MTG, YGO, Lorcana, One Piece, Sports), Qdrant embed pipeline, eBay/TCGPlayer/Cardmarket pricing ingest, FX normalization, Temporal workflows + schedules, `docs/data-sources.md`
- Weeks 6–12: scan pipeline, search + card detail + scan UX, portfolio/alerts/billing, LangGraph agent wiring (GradeROI, Monitor, Digest), portfolio CSV export, image search, eval hooks, `pnpm db:demo`
- Weeks 1–12 audit: comps source filter, PSA pop report link, eval README, portfolio test fix, docs sync
- AI condition grading v0 (heuristic) + grade-ladder ROI verdict on scan
- Vertical slice: scan UI, card detail page, dev seed data, pricing ingest CLI
- Market ladder (Card Ladder parity): `/ladder` price-guide explorer with last sold price, 30d sales volume, 1M % change, game/text filters, 5 sort modes, and load-more pagination; backed by `GET /v1/market/movers` (Redis-cached) + seed data with previous-month comps
- Population counts: `card_population` table + `GET /v1/cards/{id}/population`, pop column on the ladder, PSA breakdown on card detail, PSA pop worker source (`PSA_API_TOKEN`), seeded dev pops (migration 0004)
- Market indexes: `GET /v1/market/index` — CL50-style equal-weighted composite (rebased to 100) with per-game variants; 90d index chart on `/ladder`
- Saved searches (Pro): `saved_searches` table + `/v1/searches` CRUD, save/apply/delete chips on `/ladder`
- PWA / app-store readiness: web manifest, app icon, offline service worker (API never cached), iOS/Android install metadata, and `docs/runbooks/app-store-distribution.md` (Play Store TWA runbook; iOS Capacitor path gated on ADR)
- Multi-TCG dev seed + `pnpm db:demo`: sample cards, comps, and Qdrant embeddings for Pokemon, MTG, Yu-Gi-Oh!, Lorcana, and One Piece (scan game picker + demo cards per TCG)
- Authentication on web/API: **Supabase Auth** (Clerk removed) — SSR session cookies, protected-route middleware, sign-in/sign-up pages, `SupabaseAuthBridge` → SDK `Authorization: Bearer` JWT; API verifies via JWKS or `SUPABASE_JWT_SECRET`
- Owner/admin roles + dashboard: `UserRole` enum, account numbers (`#000010`), `/v1/admin/*` API, `/admin` dashboard (KPIs, data health, users, revenue for senior+), `OWNER_EMAIL` bootstrap
- New app shell: mobile bottom tab bar (Ladder · Shop · Scan · Indexes · More) with center Scan action, sticky desktop nav, grade badges colored by grading company
- Worldwide multi-currency display (beyond Card Ladder's USD-only): `GET /v1/market/fx` serving `fx_rate` table, daily ECB rates source (`apps/worker/sources/fx.py`, frankfurter.dev), web currency provider auto-detecting locale (GBP/EUR/JPY/CAD/AUD/CHF) with header + More-page switcher, all prices locale-formatted, comps/listings shown in their honest source currency
- Production readiness: configurable `CORS_ORIGINS` + `ENVIRONMENT`, production auth hardening (no `X-Dev-User-Id` bypass), `EBAY_MARKETPLACE_ID` default `EBAY_GB`, API/worker Dockerfiles, worker cron runbook, PWA PNG icons + `assetlinks.json`, `sitemap.ts`/`robots.ts`, next/image hosts for YGO/eBay/Lorcana/One Piece, scan beta gate in prod, search rate limiting, TCG Chart branding
- Docs accuracy pass: root `AGENTS.md` / `CLAUDE.md` / README / project tracking aligned to Supabase Auth, Temporal worker, and demo-vs-beta status; obsolete Celery/`backend/` context files marked do-not-follow
