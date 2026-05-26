# TCG Scan — Phase 1 Plan (v1.0)

> **Audience**: This document is written for two readers.
> 1. The human founder (RJ — AI/ML engineer) — to align on scope, strategy, and execution.
> 2. A future Claude / Cursor agent session — to use this as the source-of-truth context for scaffolding the repo and generating implementation prompts.
>
> **Style for the agent**: Treat every "Spec" block as a contract. Every "Cursor Prompt Seed" can be copy-pasted into Cursor / Claude Code to generate scaffolding. Do not invent features outside this document without flagging.

---

## 0. TL;DR

TCG Scan v1 is a **universal price-intelligence platform for trading cards** — web app first, mobile second, sharing one backend. The single core promise: *take a photo of any card and instantly see the last 30 days of sold prices on eBay, TCGPlayer, Cardmarket, plus every active listing, plus an AI condition + grading ROI verdict.*

We win against 130point and Card Ladder by being:
1. **Multi-TCG + sports in one app** (they are sports-only / TCG-shallow).
2. **AI-native scan-first UX** (130point's scan is bolted on, Card Ladder has no AI scan).
3. **Cross-marketplace by default** — eBay sold + TCGPlayer + Cardmarket (EU) + auction houses, deduplicated, in one card view.
4. **Agentic price intelligence** — autonomous watchers, alerts, arbitrage, anomaly/shill detection.
5. **Portfolio + grading ROI in one place** — what Card Ladder is missing.

Build approach: solo full-stack ML engineer + heavy agentic coding (Cursor 2.4 subagents, Claude Code with subagents, LangGraph for production ML/agent workflows).

---

## 1. Market & Competitor Audit

### 1.1 Direct competitors

| Competitor | Strength | Weakness we exploit |
|---|---|---|
| **130point.com** | Free; aggregates 8+ marketplaces (eBay, PWCC, Goldin, Heritage, MySlabs, Pristine); 15M+ sold items; mobile app | Sports-only focus; search-tool UX (no real portfolio); shallow TCG support; no AI condition grading; no agentic alerts |
| **Card Ladder** | Cleanest UI; sales back to 2000; portfolio tracker; Card Ladder Index; daily email; Pro tier | Sports-only; no AI scan; no grading ROI; no dealer tools; "charts without actionable intelligence" (cited gap) |
| **Market Movers (SCI)** | 2M+ cards (sports + TCG + non-sports); price alerts; collection up to 25 items free | Limited free tier; weaker scan UX; not built around camera-first |
| **Slabfy** | Dealer ops (POS, consignment, Flip Finder, grade-ladder ROI) | Dealer/business focus; expensive; not for casual collector; sports-leaning |
| **Ludex** | Strong analytics + portfolio; $7.99/mo; sports + TCG | Niche split (need separate solution per category); UI is dated |
| **Collectr** | Pokemon-collector loved; clean UI; live auctions | Slow/less reliable scanner; Pokemon-leaning |
| **CardPriceIQ** | Claimed 94% scan accuracy across Pokemon/MTG/Sports; 20+ price sources | Smaller brand; weaker portfolio |
| **Eyevo** | Pokemon-only; <1s scan, 95%+ claim | Pokemon-only |
| **TCG Radar** | Computer-vision condition assessment | Narrow audience |
| **TCGplayer official** | Marketplace-integrated scan; canonical TCG catalog | Closed ecosystem; eBay-owned; biased to TCGPlayer prices |
| **PriceCharting** | Sealed product pricing | Cards weaker than competitors |

### 1.2 Gaps in the market (our wedge)

- **No single product serves all latest TCGs (Pokemon, MTG, Yu-Gi-Oh, One Piece, Lorcana, Disney, Star Wars Unlimited, Flesh & Blood, Digimon, Weiss Schwarz, Union Arena) AND sports cards under one roof with a quality AI scanner.**
- No competitor reliably surfaces **30-day eBay sold + TCGPlayer last sold + Cardmarket EU trend + active listings** in one card detail view.
- No mainstream competitor uses **agentic AI workflows** (LangGraph / Claude / multi-agent) for autonomous price monitoring, arbitrage detection, and grading recommendations.
- Card Ladder, the user-experience leader, openly lacks AI verdicts and grading ROI — that's a direct opening.

### 1.3 Our positioning sentence

> **TCG Scan is the AI-native price intelligence platform for every modern card game and sports card — scan once, get the last 30 days of real sales, current listings, condition grade, and an AI verdict on whether to hold, sell, or grade.**

---

## 2. Phase 1 Product Scope (v1)

Phase 1 ships a **web app** that is fully usable on desktop and mobile browsers, with a **mobile-optimized PWA + camera scan flow**, backed by a **single API + ML platform** that the future native app will also consume.

### 2.1 v1 must-haves

1. **Universal card catalog**: Pokemon, MTG, Yu-Gi-Oh, One Piece, Lorcana, Disney Lorcana, Star Wars Unlimited, Flesh & Blood, Digimon, Weiss Schwarz, Union Arena, plus sports cards (baseball, basketball, football, soccer, F1, UFC). Unified `card_identity` schema across games.
2. **Card scan from photo**: web upload OR webcam capture (PWA camera intent on mobile). Returns top-K matches with confidence. Two-stage pipeline: detection → embedding ANN search → OCR re-rank.
3. **Card detail page**:
   - Last 30-day eBay sold comps (mean / median / min / max, raw vs graded breakouts).
   - Current eBay active listings (filtered, sorted by best deal).
   - TCGPlayer market price + low/mid/high (where available).
   - Cardmarket trend price + EU low (where available).
   - Auction house results (130point-style: PWCC, Goldin, Heritage, MySlabs).
   - 90-day price chart.
   - PSA/BGS/CGC pop-report links and grade-ladder ROI estimate.
4. **AI condition assessment**: from the scan image, produce an estimated PSA grade range (e.g. "8–9") plus subgrades (centering, corners, edges, surface).
5. **Portfolio**: add cards to a collection, auto-valued daily, daily-change chart, export CSV / tax-ready report.
6. **Price alerts**: "alert me when this card drops below $X" / "spikes above $X" / "PSA 10 comp lands above $X".
7. **Search**: type-to-search the catalog (name, set, number) plus image-search ("find cards that look like this").
8. **Auth + payments**: free tier (10 scans/day, no alerts), Pro tier (unlimited scans, alerts, portfolio analytics).

### 2.2 v1 stretch (ship if time)

- **Agentic Daily Brief**: every morning, a Claude-generated email/digest summarising "your collection moved +2.3%, here are 3 cards trending up, here are 2 arbitrage opportunities matching your wishlist".
- **Flip Finder**: agent that watches eBay/TCGPlayer/Cardmarket in real time and surfaces underpriced listings vs market.
- **Counterfeit / shill bid heuristic**: anomaly detection flag.

### 2.3 v1 explicit non-goals

- Native iOS/Android apps (Phase 2).
- Live auctions / our own marketplace (Phase 3).
- P2P trading (Phase 3).
- Sealed product / wax tracking (Phase 2).
- Multilingual UI (English-only at launch).

---

## 3. System Architecture

### 3.1 High-level diagram (textual)

```
┌──────────────────────────────────────────────────────────────────────┐
│  CLIENT TIER                                                          │
│  ┌────────────────────┐    ┌──────────────────────────────────────┐  │
│  │ Web (Next.js 15)   │    │ Mobile (React Native / Expo) — Phase2│  │
│  └─────────┬──────────┘    └──────────────────┬───────────────────┘  │
└────────────┼──────────────────────────────────┼──────────────────────┘
             │                                  │
             ▼                                  ▼
   ┌──────────────────────────────────────────────────────────┐
   │  EDGE / API GATEWAY — Next.js Route Handlers + Hono      │
   │  (auth, rate-limit, caching)                              │
   └─────────┬─────────────────────────────────┬───────────────┘
             │                                 │
             ▼                                 ▼
   ┌────────────────────┐         ┌─────────────────────────────┐
   │ FastAPI Core API   │         │  Agent Orchestrator         │
   │ (Python, async)    │◀────────│  LangGraph + Claude         │
   │  - card lookup     │         │  Subagents: Scan / Price /  │
   │  - portfolio       │         │  Monitor / Grade / Insights │
   │  - alerts          │         └──────────────┬──────────────┘
   └─────────┬──────────┘                        │
             │                                   │
   ┌─────────┴────────────┬───────────┬──────────┴──────────┐
   ▼                      ▼           ▼                     ▼
┌──────────────┐  ┌──────────────┐ ┌─────────────┐  ┌─────────────────┐
│ Postgres     │  │ Qdrant       │ │ Redis       │  │ S3 / R2         │
│ (Supabase)   │  │ (img embed.) │ │ (cache+queue)│ │ (card photos)  │
│ + pgvector   │  │              │ │             │  │                 │
└──────────────┘  └──────────────┘ └─────────────┘  └─────────────────┘

   ┌──────────────────────────────────────────────────────────┐
   │  ML PLATFORM (GPU on Modal / Runpod)                     │
   │  - Detection (YOLO v11)                                  │
   │  - Embedding (SigLIP / DINOv2 fine-tuned)                │
   │  - OCR (PaddleOCR / TrOCR)                               │
   │  - Condition Grader (multi-head CNN)                     │
   │  Served via BentoML / Modal endpoints                    │
   └──────────────────────────────────────────────────────────┘

   ┌──────────────────────────────────────────────────────────┐
   │  DATA INGESTION (Temporal or Celery + Redis)             │
   │  - eBay Browse + Marketplace Insights workers            │
   │  - TCGPlayer (TCG API.dev / TCGAPIs.com)                 │
   │  - Cardmarket (Apify / Poketrace)                        │
   │  - 130point-style sources (PWCC, Goldin, Heritage)       │
   │  - Catalog refreshers (Scryfall, Pokemon TCG API, YGOPRODeck) │
   └──────────────────────────────────────────────────────────┘
```

### 3.2 Tech stack (locked for v1)

| Layer | Choice | Rationale |
|---|---|---|
| Web framework | **Next.js 15 (App Router) + TypeScript** | SSR/RSC for SEO on card pages; mature; works with Vercel free tier |
| UI | **Tailwind + shadcn/ui + lucide-react** | Fast, consistent, AI-friendly to scaffold |
| Charts | **Recharts** + Lightweight Charts for price history | Industry standard |
| Mobile (Phase 2) | **React Native + Expo** | Share TS types/SDK with web |
| Backend | **FastAPI (Python 3.12) + Pydantic v2** | Plays perfectly with our ML stack; user is Python/ML native |
| Auth | **Clerk** | Fast setup, supports orgs (for future dealer tier) |
| DB (transactional) | **PostgreSQL 16 via Supabase** | Free tier good; pgvector built in |
| Vector DB (images) | **Qdrant Cloud** (free tier ~1GB) or self-hosted | Rust, fast, payload filtering, image-search proven at scale |
| Cache / queue | **Redis (Upstash)** | Serverless, generous free tier |
| Workflow / agents | **LangGraph + Claude (Sonnet 4.6 + Haiku 4.5)** | Production-grade agentic; LangSmith tracing |
| Background workers | **Temporal Cloud** (preferred) or Celery | Durable executions for long price-watching workflows |
| ML serving | **Modal.com** (GPU pay-per-second) | No infra; deploys from Python; great DX |
| Object storage | **Cloudflare R2** | S3-compatible, no egress fees |
| Payments | **Stripe** | Standard |
| Observability | **OpenTelemetry → Grafana Cloud (free)**, **LangSmith** for agent traces, **Sentry** for errors | Production-grade |
| CI/CD | **GitHub Actions** + Vercel + Modal deploy | Standard |
| Monorepo | **Turborepo + pnpm** | First-class for Next.js + RN + shared TS packages |

### 3.3 Repo layout (monorepo, Turborepo)

```
tcg-scan/
├── apps/
│   ├── web/                   # Next.js 15 app
│   ├── api/                   # FastAPI service
│   ├── worker/                # Temporal/Celery workers (Python)
│   └── ml/                    # Modal deployments + model code
├── packages/
│   ├── sdk-ts/                # Generated TS client from OpenAPI
│   ├── sdk-py/                # Python client (internal)
│   ├── ui/                    # shadcn-based component library
│   ├── schema/                # Zod + Pydantic models shared via JSON Schema
│   └── agents/                # LangGraph graphs (Python)
├── infra/
│   ├── docker/                # Local dev (postgres, qdrant, redis)
│   ├── terraform/             # Cloud infra
│   └── github/                # Reusable workflows
├── data/
│   ├── catalog-ingest/        # Catalog ETL scripts
│   └── seeds/                 # Local dev seeds
├── docs/
│   ├── adr/                   # Architecture decision records
│   └── runbooks/              # Ops runbooks
├── .cursor/
│   └── rules/                 # Cursor rules per package
├── AGENTS.md                  # Root agent guidance
├── CLAUDE.md                  # Repo conventions for Claude Code
├── turbo.json
└── pnpm-workspace.yaml
```

Each `apps/*` and `packages/*` has its own `AGENTS.md` so Cursor subagents pick up local conventions automatically.

---

## 4. Data Strategy

### 4.1 Card identity (catalog) — the foundation

Unified `card_identity` row covers every game. Sources, all free or low-cost:

| Game | Source | Notes |
|---|---|---|
| Pokemon | pokemontcg.io API | Free, includes images + sets |
| Magic: The Gathering | Scryfall API | Free, gold standard, includes prices |
| Yu-Gi-Oh | YGOPRODeck API | Free |
| One Piece | one-piece-cardgame.dev / Scryfall-like community | Community |
| Lorcana | lorcast.com API | Free |
| Star Wars Unlimited | swudb.com | Community |
| Flesh & Blood | fabdb.net | Community |
| Digimon | digimoncard.io | Community |
| Sports | Custom ingest (TCG API / TCGAPIs / scraped) | Paid tier later |

**Schema** (simplified):
```
card_identity (
  id uuid pk,
  game enum,                      -- 'pokemon' | 'mtg' | 'sports_baseball' | ...
  name text,
  set_code text,
  set_name text,
  number text,                    -- "199/198" etc
  rarity text,
  variants jsonb,                 -- holo, reverse, 1st-edition, parallel
  attributes jsonb,               -- game-specific (HP, mana_cost, attack, year, manufacturer, player)
  image_urls jsonb,               -- front, back, hi-res
  external_ids jsonb,             -- {tcgplayer_id, cardmarket_id, ebay_epid, ygoprodeck_id}
  embedding vector(1024),         -- visual embedding (also mirrored in Qdrant)
  created_at, updated_at
)
```

### 4.2 Pricing ingestion

| Source | Method | Status | Fallback |
|---|---|---|---|
| eBay Browse API (active listings) | Official, public | Approved on signup | n/a |
| eBay Marketplace Insights (90d sold) | Official, **limited release** — apply Day 1 | May take weeks; apply early | Browse + completed-listings scraper |
| TCGPlayer (TCG-specific market prices) | TCG API (tcgapi.dev) or TCGAPIs.com | Paid ($9.99–$99/mo) | Scryfall passthrough for MTG |
| Cardmarket (EU) | Not accepting new apps → Apify scrapers / Poketrace | Apify ~$0.x/run | Manual scrape fallback |
| Heritage / PWCC / Goldin / MySlabs | Public sale pages; scheduled scrape | Reasonable; mind ToS | n/a |
| Pokemon TCG / MTG price hints | Scryfall (MTG), pokemontcg.io | Free | n/a |

**Storage**: every comp is normalized into a `sale_event` row keyed to a `card_identity.id` with `(source, sold_at, price, currency, grade, condition, listing_url, raw_payload)`. Daily roll-ups land in `card_price_daily` for fast chart queries.

### 4.3 Data freshness SLOs

- Active eBay listings: refresh popular cards every 15 min, long-tail every 6h.
- Sold comps: hourly polling on top 10k cards, daily on the rest.
- Catalog: full refresh weekly; on-demand for new sets.

---

## 5. AI / ML Pipelines

### 5.1 Card scan pipeline (end-to-end target latency < 2.5s on web)

```
photo upload
   │
   ▼
[1] Detection — YOLOv11-nano fine-tuned on cards (axis-aligned + rotated bbox)
   │     output: cropped card region(s), rotation-corrected
   ▼
[2] Visual embedding — SigLIP-2 / DINOv2 fine-tuned (contrastive on card_identity)
   │     output: 1024-dim vector
   ▼
[3] ANN search in Qdrant — top-K (K=20) candidates
   │     filtered by detected game (from set-symbol classifier or user hint)
   ▼
[4] OCR — PaddleOCR for name/number/set; cross-check vs candidates
   │     output: re-ranked top-K
   ▼
[5] Final selection — argmax of joint score (cos-sim * OCR-match * popularity prior)
   │     output: card_identity_id + confidence
   ▼
[6] Condition grading — multi-head ResNet/EfficientNet predicting
        {centering_x, centering_y, corners, edges, surface, overall}
   │
   ▼
[7] Compose result — return card + 30d comps + condition + grade-ladder ROI
```

### 5.2 Training data plan

- **Catalog images**: hi-res from official APIs (Scryfall / pokemontcg.io) — used to pretrain embeddings via self-supervised contrastive on augmentations (random crop, blur, glare simulation, perspective).
- **Real-world photos**: bootstrap with user uploads (consent-gated); seed with public datasets (eBay listing crawl images) + a few hundred hand-shot reference photos per major TCG.
- **Condition labels**: scrape eBay listings where seller declares PSA grade → align listing image with grade label. Filter heavily for trustworthiness. Augment with controlled photography on known graded slabs (buy 20–30 slabs per grade tier).

### 5.3 Model serving

All models served as Modal endpoints, autoscaling on GPU, with a CPU fallback for embeddings. Each endpoint exposes a stable JSON contract documented in `apps/ml/contracts.md`.

### 5.4 Evaluation harness (must-have before launch)

- Held-out set per game: 500+ photos, hand-labeled.
- Metrics: top-1 accuracy, top-5 accuracy, mean confidence, p50/p95 latency, condition MAE vs ground-truth grade.
- CI runs eval on every model PR; gates merges.

---

## 6. Agentic Layer

We use **LangGraph** as the orchestrator. Each subagent is a node with its own toolset and is independently testable.

### 6.1 Subagents

| Agent | Trigger | Tools | Output |
|---|---|---|---|
| **ScanAgent** | User uploads photo | detection / embedding / OCR / grader | `card_match`, `condition` |
| **PricingAgent** | After scan / on card detail load | `ebay_browse`, `ebay_insights`, `tcgplayer_lookup`, `cardmarket_lookup`, `auction_house_lookup` | `comps_30d`, `active_listings`, `chart_series` |
| **GradeROIAgent** | After ScanAgent + PricingAgent | grade-ladder pricing lookup, grading-cost table | BUY / SELL / HOLD / GRADE verdict + expected $ delta |
| **MonitorAgent** (long-running) | User sets alert | scheduled poll via Temporal | push notification, email |
| **FlipFinderAgent** (Phase 1 stretch) | Continuous | listing stream + price model | ranked underpriced listings |
| **AnomalyAgent** | On sale-event ingest | statistical + LLM judge | suspicious sale flag |
| **DigestAgent** | Daily cron per user | LLM over portfolio + market diff | personalized briefing |

### 6.2 Why LangGraph (and not CrewAI alone)

- Stateful, branching workflows with retries, human-in-the-loop hooks, and replayable traces via LangSmith — exactly what we need for production agentic flows that touch real money decisions.
- CrewAI is great for prototyping; we can use it locally for spikes, but the production system is LangGraph.

### 6.3 LLM cost discipline

- Default to **Claude Haiku 4.5** for routing, classification, and summarisation.
- Use **Claude Sonnet 4.6** only for synthesis (Digest, GradeROI verdict, AnomalyAgent judgment).
- Every agent call is wrapped in a cost-budget guard (`max_input_tokens`, `max_output_tokens`); LangSmith dashboards track $/scan and $/active-user.

---

## 7. UX / UI Plan (v1 web)

Pages:

1. **Landing** — value prop, demo scan video, "Try a scan" CTA (no login required for first 3 scans).
2. **Scan** — drag-drop / camera capture, live preview of detection box, result card slides up.
3. **Card detail** — hero image + condition badge + price summary tiles + 90d chart + comps table (filterable by source / grade) + grade-ladder ROI panel + "add to portfolio" / "set alert".
4. **Search** — text + image search, filters by game / set / rarity.
5. **Portfolio dashboard** — total value, daily-change spark, top movers, grade distribution, suggested actions.
6. **Alerts** — list, create, edit.
7. **Account / billing** — Stripe portal.
8. **Admin / data quality** — internal-only, see ingest health.

Design principles:
- Mobile-first responsive (web is the primary surface for v1).
- Camera-prominent on mobile breakpoints.
- Card detail is shareable + SEO-optimised (each card is an indexable page — huge long-tail SEO play vs Card Ladder which gates content).

---

## 8. Roadmap (90 days, solo)

| Week | Milestone | Deliverable |
|---|---|---|
| 1 | Repo + infra | Monorepo bootstrapped, CI green, Postgres + Qdrant + Redis local; Modal account; Vercel project; AGENTS.md + CLAUDE.md committed |
| 2 | Catalog ingest | Pokemon + MTG + YGO catalogs fully ingested with images; `card_identity` populated; image embedding job runs end-to-end |
| 3 | Catalog completion | Lorcana + One Piece + Sports MVP (top 20k cards); Qdrant index live |
| 4 | eBay ingest (Browse + Insights apply) | Active-listing fetcher + sold-comp fetcher; `sale_event` table populated; daily roll-ups |
| 5 | TCGPlayer + Cardmarket | Third-party API or scraper wired in; comps normalised across sources |
| 6 | Scan API v0 | Detection + embedding ANN search live; top-K endpoint returns matches at <2.5s p95 |
| 7 | Scan refinement | OCR re-rank + game-prior; condition grader v0 trained on bootstrap data |
| 8 | Web app: search + card detail | Public, indexable, fast |
| 9 | Web app: scan flow | Webcam + upload, result UI polished |
| 10 | Auth + portfolio + alerts | Clerk + Stripe + Temporal scheduled jobs |
| 11 | Agentic layer | LangGraph wiring up ScanAgent → PricingAgent → GradeROIAgent; DigestAgent stretch |
| 12 | Hardening + private beta | Eval harness, observability dashboards, 25-user closed beta, bug burndown |

Buffer week 13 for launch polish.

---

## 9. KPIs (Phase 1 success criteria)

- **Scan accuracy**: top-1 ≥ 90% across all supported games on held-out eval; top-5 ≥ 98%.
- **Scan latency**: p95 < 2.5s end-to-end on web.
- **Price freshness**: ≥ 95% of top-10k cards have a comp from the last 24h.
- **Coverage**: every supported game has ≥ 95% of in-print cards indexed.
- **Beta NPS** ≥ 40 after 4 weeks of closed beta.
- **Unit economics**: LLM cost per Pro user < $0.30/month at projected usage.

---

## 10. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| eBay Marketplace Insights rejection | Medium | Apply Day 1; fall back to Browse API + permitted scraping of completed listings; partner with Poketrace as bridge |
| TCGPlayer API still closed | High | Use TCG API.dev / TCGAPIs.com as primary; budget $50–$100/mo |
| Cardmarket data quality | Medium | Use Apify Cardmarket Trend scraper; cache aggressively |
| Model accuracy below target | Medium | Tiered scan UI (top-K with confirm step); active learning loop from user confirmations |
| Scraping ToS / legal | Medium | Stick to official APIs where possible; document compliance in `docs/legal/`; respect robots and rate limits |
| Solo founder burnout | Always | Strict scope discipline; weekly review against this plan; agent-assisted coding to maintain throughput |
| Cost overrun on GPUs | Low/Medium | Modal pay-per-second + CPU fallback + caching of embeddings |

---

## 11. Phase 2 & 3 preview (out of v1 scope but informs v1 design)

- **Phase 2 (months 4–6)**: Native iOS/Android (React Native), live grading via video stream, sealed product, dealer/POS tier (Slabfy-competitive), affiliate revenue from eBay + TCGPlayer + Cardmarket.
- **Phase 3 (months 7–12)**: In-app marketplace (escrow, shipping, authentication), live auctions, social/feed, ML price forecasting models.

---

## 12. Instructions for the next Claude / Cursor session (scaffolding)

> When the next session starts, the user will share this file. Treat the following as a stepwise prompt menu.

### 12.1 Step 0 — Verify

Read this entire document. If anything is ambiguous, ask before generating code.

### 12.2 Step 1 — Scaffold the monorepo

**Cursor Prompt Seed**:
```
Read TCG_Scan_Phase1.md (§3.3 repo layout, §3.2 tech stack).
Bootstrap a Turborepo monorepo with pnpm workspaces named "tcg-scan".
Create apps/web (Next.js 15 App Router + TS + Tailwind + shadcn/ui),
apps/api (FastAPI + Pydantic v2 + uv-managed),
apps/worker (Python, Temporal SDK skeleton),
apps/ml (Modal stub),
packages/sdk-ts, packages/sdk-py, packages/ui, packages/schema, packages/agents.
Add infra/docker/docker-compose.yml with postgres-16, qdrant, redis.
Add AGENTS.md at root and per package with §6 conventions.
Add a top-level CLAUDE.md summarising §3 of the plan.
Add GitHub Actions: lint+typecheck+test on PR; release on main.
Do NOT add product code yet — scaffolding only.
```

### 12.3 Step 2 — Catalog ingest

**Cursor Prompt Seed**:
```
Implement apps/worker/catalog/ ingesters for Pokemon (pokemontcg.io), MTG (Scryfall), Yu-Gi-Oh (YGOPRODeck), Lorcana (lorcast). 
Conform output to packages/schema/card_identity.json (Pydantic + Zod).
Write Postgres migrations for card_identity, sale_event, card_price_daily. Use Alembic.
Provide an idempotent CLI: `pnpm worker ingest:catalog --game pokemon`.
Add a job that computes a 1024-dim DINOv2 embedding per card image and upserts to Qdrant collection `cards`.
Write integration tests against a local docker-compose stack.
```

### 12.4 Step 3 — Pricing ingest

**Cursor Prompt Seed**:
```
Implement apps/worker/pricing/ with three workers:
- ebay_active.py: eBay Browse API → normalize → sale_event (kind=listing)
- ebay_sold.py: Marketplace Insights → normalize → sale_event (kind=sold). 
  If credentials missing, fall back to documented Browse-only mode and log a warning.
- tcgplayer.py + cardmarket.py: pluggable provider interface, default to TCG API.dev.
All workers run as Temporal scheduled workflows. Add retries + circuit breakers.
Compute card_price_daily roll-ups (mean/median/min/max raw vs graded) via a nightly job.
```

### 12.5 Step 4 — Scan API + ML

**Cursor Prompt Seed**:
```
In apps/ml, deploy four Modal endpoints behind a single `scan()` orchestrator:
1. detect: YOLOv11-nano (start with the public ultralytics model, fine-tune later).
2. embed: DINOv2-base, mean-pool, L2-normalize.
3. ocr: PaddleOCR (server mode).
4. grade: ResNet50 multi-head; ship with a placeholder weights file and a TODO to train on labeled data.
Expose a FastAPI endpoint `/v1/scan` in apps/api that:
- accepts an image,
- calls detect → embed,
- queries Qdrant top-20 (with game filter if user supplied),
- calls ocr on the crop and re-ranks,
- returns top-K matches with confidences and a condition estimate.
Target p95 < 2.5s; cache embeddings of recently-seen photos in Redis.
```

### 12.6 Step 5 — Web app

**Cursor Prompt Seed**:
```
Build apps/web pages per §7:
- /                 landing with demo
- /scan             upload + webcam capture (use getUserMedia, fallback to file input)
- /card/[slug]      SSR card detail with price tiles, 90d chart, comps table
- /search           text + image search
- /portfolio        Clerk-gated dashboard
- /alerts           CRUD
- /account          Stripe customer portal
Use packages/sdk-ts (generated from apps/api OpenAPI) for all API calls.
Mobile-first responsive. SEO: each /card/[slug] is statically generated then ISR-refreshed.
```

### 12.7 Step 6 — Agentic layer

**Cursor Prompt Seed**:
```
In packages/agents, implement LangGraph graphs:
- scan_graph: ScanAgent → PricingAgent → GradeROIAgent.
- monitor_graph: scheduled MonitorAgent (Temporal worker schedules it; LangGraph executes the node logic).
- digest_graph: nightly DigestAgent per user.
Use Claude Haiku 4.5 by default; escalate to Sonnet 4.6 for GradeROIAgent + DigestAgent synthesis.
Wrap every node with LangSmith tracing and a token/cost budget guard.
Expose graphs as functions imported by apps/api (sync) and apps/worker (async).
```

### 12.8 Step 7 — Eval harness + observability

**Cursor Prompt Seed**:
```
Create apps/ml/eval/ with a held-out test set runner. CSV input: image_path, true_card_id, true_grade.
Compute top-1, top-5, condition MAE, p50/p95 latency. Output JSON + markdown report.
Wire to GitHub Actions: PRs touching apps/ml or packages/agents must run the eval and post a comment.
Set up OpenTelemetry export from apps/api + apps/worker to Grafana Cloud Free.
Configure Sentry on web + api + worker. Configure LangSmith project `tcg-scan-prod`.
```

### 12.9 Step 8 — Beta launch checklist

Cross-check §9 KPIs before flipping the gate. Run the deploy-checklist skill.

---

## 13. Open questions for RJ

1. **Region for v1**: US-first (eBay USD), UK/EU (Cardmarket), or global from day 1? Default assumption: US-first, EU price layer included.
2. **Affiliate revenue**: enable eBay Partner Network + TCGPlayer affiliate from day 1? (Free money; needs disclosure UX.)
3. **Brand**: TCG Scan final, or candidate names (TCG Lens, CardSight, ScanLadder)?
4. **Pricing tiers**: my default — Free (10 scans/day, 25 portfolio items), Pro $9.99/mo (unlimited scans, unlimited portfolio, alerts, daily digest), Dealer $39/mo (Phase 2). Acceptable?
5. **Grading partnership**: pursue affiliate / referral with PSA / SGC / CGC in Phase 2? (Bigger margin than ads.)

---

## 14. Sources & references

- 130point — feature set, mobile app, marketplaces aggregated (https://130point.com/, https://apps.apple.com/us/app/130-point/id6504721152, https://diversinet.com/130point/)
- Card Ladder — Pro features, portfolio tracker, pricing tiers (https://www.cardladder.com/, https://www.cardladder.com/pricing, https://www.cardladder.com/why-card-ladder)
- Slabfy alternatives roundup — competitive landscape (https://slabfy.com/blog/card-ladder-alternative, https://slabfy.com/blog/best-sports-card-apps-2026)
- Eyevo Pokemon scanner comparison (https://eyevotcg.com/blog/best-pokemon-card-scanner-apps-2026/)
- CardPriceIQ tested scanner ranking (https://cardpriceiq.com/news/best-card-scanner-apps-2026)
- Ludex (https://www.ludex.com/)
- Collectr (https://getcollectr.com/)
- Market Movers (https://www.marketmoversapp.com/)
- TCG Radar / CardGrader / CardGrade.io / TCG AI PRO (https://cardgrader.ai/, https://cardgrade.io/, https://tcgai.pro/)
- eBay Marketplace Insights API (https://developer.ebay.com/api-docs/buy/marketplace-insights/static/overview.html)
- TCGPlayer API status & alternatives (https://tcgapi.dev/, https://tcgapis.com/)
- Cardmarket API status (https://help.cardmarket.com/en/cardmarket-api)
- Poketrace dev API (https://poketrace.com/developers)
- LangGraph vs CrewAI vs AutoGen production guidance (https://alicelabs.ai/en/insights/best-ai-agent-frameworks-2026, https://47billion.com/blog/ai-agents-in-production-frameworks-protocols-and-what-actually-works-in-2026/)
- Cursor 2.4 subagents + AGENTS.md standard (https://www.aimakers.co/blog/cursor-2-4-subagents/, https://vibecoding.app/blog/agents-md-guide)
- Vector DB comparison (https://medium.com/data-science-collective/pinecone-vs-weaviate-vs-qdrant-vs-milvus-66d5bfbcc460, https://www.datacamp.com/blog/the-top-5-vector-databases)

---

*End of Phase 1 plan v1.0.*
