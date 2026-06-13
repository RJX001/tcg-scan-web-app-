# Changelog

## Unreleased

### Added

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
- Clerk authentication on web: `@clerk/nextjs` middleware (portfolio/watchlist/alerts/account gated), sign-in/sign-up pages, header auth UI, SDK `Authorization: Bearer` token injection via `AuthBridge`
- Owner/admin roles + dashboard: `UserRole` enum, account numbers (`#000010`), `/v1/admin/*` API, `/admin` dashboard (KPIs, data health, users, revenue for senior+), `OWNER_EMAIL` bootstrap
- New app shell: mobile bottom tab bar (Ladder · Shop · Scan · Indexes · More) with center Scan action, sticky desktop nav, grade badges colored by grading company
- Worldwide multi-currency display (beyond Card Ladder's USD-only): `GET /v1/market/fx` serving `fx_rate` table, daily ECB rates source (`apps/worker/sources/fx.py`, frankfurter.dev), web currency provider auto-detecting locale (GBP/EUR/JPY/CAD/AUD/CHF) with header + More-page switcher, all prices locale-formatted, comps/listings shown in their honest source currency
- Production readiness: configurable `CORS_ORIGINS` + `ENVIRONMENT`, production auth hardening (no `X-Dev-User-Id` bypass), `EBAY_MARKETPLACE_ID` default `EBAY_GB`, API/worker Dockerfiles, worker cron runbook, PWA PNG icons + `assetlinks.json`, `sitemap.ts`/`robots.ts`, next/image hosts for YGO/eBay/Lorcana/One Piece, scan beta gate in prod, search rate limiting, TCG Chart branding
