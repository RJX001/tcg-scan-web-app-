# OBSOLETE — DO NOT USE FOR ARCHITECTURE OR SPRINT WORK

> **This file describes an abandoned layout** (`backend/` + `frontend/` + Celery + Next.js 14 + Clerk/password sketch).
> The live monorepo is `apps/{web,api,worker,ml}` + `packages/*` with **Temporal**, **Supabase Auth**, and Pro at **$9.99/mo**.
>
> Use instead: **`AGENTS.md`**, **`CLAUDE.md`**, **`docs/TCG_Scan_Phase1.md`**, **`docs/PROJECT_TRACKING.md`**.
> Kept only for historical reference. Last useful update: May 2026.

---

# TCG SCAN PHASE 1 — CURSOR CONTEXT FILE (ARCHIVED)
# Last updated: May 2026

---

## WHAT WE ARE BUILDING

Product: TCG Scan Phase 1 — AI-native price intelligence platform for TCG collectors
Competitor: CardLadder (sports only, no AI) — we beat them on TCG coverage + AI agents
Price: Free tier + Pro at £5.99/month  ← **obsolete; live docs use $9.99/mo**
Stack: FastAPI + PostgreSQL + Redis + Celery + Next.js 14 + LangGraph  ← **obsolete**
Repo root: tcg-scan-phase-1/  ← **obsolete**

---

## THE ONE RULE THAT MATTERS MOST

The frontend NEVER calls eBay, TCGplayer, Cardmarket or any external API directly.
All external data is fetched by Celery workers in backend/app/sources/.
All data is normalised into our PostgreSQL database.
The frontend only ever calls OUR FastAPI at NEXT_PUBLIC_API_URL.

---

## TECH STACK QUICK REFERENCE

| Layer         | Technology                                    |
|---------------|-----------------------------------------------|
| Backend API   | FastAPI (Python 3.11) + Pydantic v2           |
| Database      | PostgreSQL 15 via PgBouncer (port 6432)       |
| ORM           | SQLAlchemy 2 + Alembic migrations             |
| Cache         | Redis 7 — price cache TTL 15min               |
| Background    | Celery 5 + Redis broker                       |
| AI Agents     | LangGraph + Claude Sonnet 4.6                 |
| Frontend      | Next.js 14 App Router + TypeScript strict     |
| Styling       | Tailwind CSS                                  |
| State         | Zustand (auth) + React Query (server state)   |
| Payments      | Stripe Checkout + Webhooks + Customer Portal  |
| Monitoring    | Sentry + PostHog                              |

---

## DATABASE TABLES (all 14)

| Table                | Key columns                                                    | Notes                          |
|----------------------|----------------------------------------------------------------|--------------------------------|
| games                | id, name, slug, is_active                                      | 5 games seeded                 |
| sets                 | id, game_id, name, code, release_date                          | FK to games                    |
| cards                | id, set_id, game_id, name, number, rarity, image_url           | 200k+ rows at scale            |
| grades               | id, label, grading_company                                     | 17 grades seeded               |
| card_sales           | id, card_id, grade_id, platform, sale_price, currency, sale_date | Source of truth for prices   |
| card_values          | id, card_id, grade_id, value_gbp, sample_count, computed_at    | Nightly computed, unique card+grade |
| market_index         | id, game_id, index_value, change_pct_24h, change_pct_7d        | Daily per game                 |
| users                | id (UUID), email, hashed_password, tier, stripe_customer_id   | tier: free or pro              |
| portfolio_holdings   | id, user_id, card_id, grade_id, purchase_price_gbp, quantity   | User holdings                  |
| price_alerts         | id, user_id, card_id, grade_id, target_price_gbp, direction    | direction: above or below      |
| market_pulse         | id, game_id, headline, summary, notable_cards (JSONB), sentiment | AI agent output, daily        |
| portfolio_advice     | id, user_id, advice_json (JSONB), generated_at                 | AI agent output, per user      |
| price_forecasts      | id, card_id, grade_id, forecast_json (JSONB), expires_at       | AI agent output, 24h cache     |

---

## API ENDPOINTS (all built, routes wired)

| Endpoint                              | Method           | Auth | Tier                        |
|---------------------------------------|------------------|------|-----------------------------|
| /api/v1/health                        | GET              | No   | All                         |
| /api/v1/auth/register                 | POST             | No   | All                         |
| /api/v1/auth/login                    | POST             | No   | All                         |
| /api/v1/auth/me                       | GET              | Yes  | All                         |
| /api/v1/cards                         | GET              | No   | All                         |
| /api/v1/cards/{id}                    | GET              | No   | All                         |
| /api/v1/cards/{id}/history            | GET              | No   | Free: 30d / Pro: all time   |
| /api/v1/market/index                  | GET              | No   | All                         |
| /api/v1/market/pulse                  | GET              | No   | Free: summary / Pro: full   |
| /api/v1/portfolio                     | GET/POST/DELETE  | Yes  | Free: 10 cards / Pro: unlimited |
| /api/v1/portfolio/export              | GET              | Yes  | Pro only                    |
| /api/v1/alerts                        | GET/POST/PUT/DELETE | Yes | Free: 5 / Pro: unlimited  |
| /api/v1/billing/create-checkout-session | POST           | Yes  | All                         |
| /api/v1/billing/webhook               | POST             | No   | Stripe signature only       |
| /api/v1/billing/status                | GET              | Yes  | All                         |
| /api/v1/billing/portal                | GET              | Yes  | Pro only                    |

---

## DATA SOURCES — RISK RULES (CRITICAL)

| Source                  | Status          | Notes                                                         |
|-------------------------|-----------------|---------------------------------------------------------------|
| eBay Browse API         | ACTIVE          | Official API. Free 5k calls/day. Set EBAY_APP_ID.            |
| Scryfall (MTG)          | ACTIVE          | Free, no key needed. Rate limit 10/sec.                       |
| Pokémon TCG IO          | ACTIVE          | Free catalogue. ~18,000 cards.                                |
| YGOPRODECK              | ACTIVE          | Free catalogue. No rate limit issues.                         |
| Reddit API              | ACTIVE          | Official. Set REDDIT_CLIENT_ID for sentiment.                 |
| Cardmarket (Apify)      | STOPGAP         | Max 500 cards/day. EU off-peak only. DISABLED by default.     |
| TCGAPIs (paid)          | NOT YET         | Subscribe at £500 MRR. Licensed TCGplayer + Cardmarket data.  |
| eBay HTML scraping      | FORBIDDEN       | Use Browse API instead. See .cursorrules.                     |
| TCGplayer direct        | FORBIDDEN       | eBay-owned, API closed. Use TCGAPIs when subscribed.          |

---

## AI AGENTS (4 agents, all gated by ENABLE_AI_AGENTS=false)

| Agent              | File                                    | Trigger                        | Tier     | Status                        |
|--------------------|-----------------------------------------|-------------------------------|----------|-------------------------------|
| Market Pulse       | app/agents/market_pulse/__init__.py     | Celery beat 07:00 UTC daily   | Free+Pro | LangGraph graph built         |
| Portfolio Advisor  | app/agents/portfolio_advisor/__init__.py | On portfolio save + Sun 8AM  | Pro only | Stub — implement Sprint 6     |
| Price Forecast     | app/agents/price_forecast/__init__.py   | Lazy on Pro card detail view  | Pro only | Stub — implement Sprint 6     |
| Deal Scanner       | app/agents/deal_scanner/__init__.py     | Every 30 minutes              | Pro only | Stub — implement Sprint 6     |

Model for ALL agents: claude-sonnet-4-6
Never change model without explicit instruction.

---

## FRONTEND PAGES (all built)

| Route              | Auth     | What is built                                         |
|--------------------|----------|-------------------------------------------------------|
| /                  | Public   | Hero, feature highlights, CTA                         |
| /search            | Public   | Card search with game tabs, React Query, debounce     |
| /cards/[id]        | Public   | SSG + ISR. Values table, recent sales, SEO meta       |
| /market            | Public   | TCG index + Market Pulse + ProGate on notable cards   |
| /portfolio         | Required | P&L summary, holdings table, free limit banner        |
| /alerts            | Required | Alert list, toggle, deal scanner section              |
| /upgrade           | Public   | Pricing page — Stripe Checkout trigger                |
| /account           | Required | Profile, billing status, Stripe portal                |
| /auth/login        | Public   | Email + password login                                |
| /auth/register     | Public   | Registration with confirm password                    |

---

## FREE vs PRO GATING

| Feature                    | Free              | Pro                  |
|----------------------------|-------------------|----------------------|
| Card search + prices       | Unlimited         | Unlimited            |
| Price history              | Last 30 days      | All time             |
| Market Pulse               | Headline only     | Full + notable cards |
| Portfolio                  | Max 10 cards      | Unlimited            |
| Price alerts               | Max 5 active      | Unlimited            |
| Portfolio Advisor Agent    | Not available     | Full recommendations |
| Price Forecast Agent       | Not available     | 7/30/90-day forecast |
| Deal Scanner alerts        | Not available     | Up to 10/day         |
| Portfolio export (CSV)     | Not available     | Full export          |

IMPORTANT: Frontend gating (useSubscription hook) is convenience only.
Backend ALWAYS enforces via check_subscription_tier() dependency.
Never trust frontend gating alone.

---

## KEY FILES TO KNOW

### Backend
- app/main.py — FastAPI entrypoint, CORS, Sentry, rate limiting
- app/core/config.py — all settings via pydantic Settings, never os.environ
- app/core/database.py — async engine (FastAPI) + sync engine (Celery)
- app/core/auth.py — JWT helpers + get_current_user_id dependency
- app/core/cache.py — Redis wrapper, all keys prefixed pi:
- app/models/ — SQLAlchemy 2 models with UUID PKs
- app/repositories/ — DB query layer (cards, users, portfolio, alerts)
- app/services/ — business logic (auth, cards, portfolio, alerts, market)
- app/api/v1/routes/ — all route handlers
- app/sources/ — THE ONLY PLACE that calls external APIs
- app/tasks/celery_app.py — beat schedule (eBay 4h, Cardmarket 03:00 UTC, agents 07:00 UTC)
- alembic/versions/001_initial.py — full schema + seeds 5 games + 17 grades

### Frontend
- src/lib/api/client.ts — Axios, only calls NEXT_PUBLIC_API_URL, attaches JWT
- src/lib/api/*.ts — one file per resource: cards, auth, portfolio, alerts, market, billing
- src/stores/auth.ts — Zustand auth store, persisted to localStorage
- src/hooks/use-subscription.ts — isPro check for frontend gating
- src/components/pro-gate.tsx — wraps Pro-only UI
- src/components/nav.tsx — sticky nav with auth-aware links
- src/styles/tokens.ts — design tokens, never hardcode colours

---

## ENVIRONMENT VARIABLES (all in backend/.env.example)

DATABASE_URL=postgresql+asyncpg://tcg:tcg@localhost:5432/tcg_scan_phase1
SYNC_DATABASE_URL=postgresql+psycopg2://tcg:tcg@localhost:5432/tcg_scan_phase1
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
SECRET_KEY=<64 char random string>
ANTHROPIC_API_KEY=<your key>
CLAUDE_MODEL=claude-sonnet-4-6
ENABLE_AI_AGENTS=false
EBAY_APP_ID=<your eBay developer app ID>
EBAY_AFFILIATE_TRACKING_ID=<EPN tracking ID>
EBAY_AFFILIATE_CAMPAIGN_ID=<EPN campaign ID>
TCGAPIS_API_KEY=<subscribe at £500 MRR>
TCGAPIS_ENABLED=false
APIFY_API_TOKEN=<for Cardmarket stopgap>
CARDMARKET_SCRAPER_ENABLED=false
REDDIT_CLIENT_ID=<for sentiment>
REDDIT_CLIENT_SECRET=<for sentiment>
STRIPE_SECRET_KEY=<sk_live_...>
STRIPE_WEBHOOK_SECRET=<whsec_...>
STRIPE_PRICE_ID_PRO_MONTHLY=<price_xxx>
STRIPE_PRICE_ID_PRO_ANNUAL=<price_xxx>
RESEND_API_KEY=<email service>
SENTRY_DSN=<your DSN>
NEXT_PUBLIC_API_URL=http://localhost:8000

---

## SPRINT MAP — WHAT GETS BUILT WHEN

| Sprint | Backend                                              | Frontend                                    |
|--------|------------------------------------------------------|---------------------------------------------|
| 1      | Catalogue clients (PTCGIO, Scryfall, YGOPRODECK) + eBay Browse API + compute_tcg_values() | — |
| 2      | CardRepository.search() tsvector + wire all route handlers + auth service | — |
| 3      | —                                                    | Home market index + card search + card detail |
| 4      | Portfolio P&L enrichment (join card_values, compute unrealised_pnl) | Portfolio page fully wired |
| 5      | Alert evaluation task + notifications + Cardmarket scraper + Reddit sentiment | Alerts page, deal scanner |
| 6      | All 4 LangGraph agents fully implemented             | Market Pulse feed + Portfolio Insights panel |
| 7      | Stripe webhook tier update + Pro route enforcement   | Upgrade page + eBay affiliate audit         |
| 8      | DB indexes + Redis warm-up + Sentry audit            | SEO meta + sitemap + Lighthouse             |

---

## HOW TO START EACH SPRINT IN CURSOR

Open Cursor Agent (Ctrl+I / Cmd+I)
Drag in: .cursorrules + this file + the specific files for that sprint
First message every session:

  Read .cursorrules. Confirm you have read it.
  Then read CURSOR_CONTEXT.md. Confirm you understand the architecture.
  We are working on Sprint [X].
  Task: [paste task from sprint map above]

---

## WHEN SOMETHING BREAKS

1. Read the full error — never guess
2. Check .cursorrules — is this a rules violation?
3. Fix at root cause — never patch symptoms
4. Run tests — do not mark done if tests fail
5. If fix requires architecture change, stop and flag it
