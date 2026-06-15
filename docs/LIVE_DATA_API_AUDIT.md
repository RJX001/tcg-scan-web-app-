# Live data API audit

Date: 2026-06-15  
Scope: Audit only — no risky schema rewrites, no auth/Stripe/CORS/UI changes.

---

## Architecture (locked)

| Layer | Responsibility |
|-------|----------------|
| **Vercel (`apps/web`)** | Calls `NEXT_PUBLIC_API_URL` only — never external TCG/Stripe secrets |
| **Railway API (`apps/api`)** | Reads Postgres/Qdrant/Redis; serves `/v1/cards`, `/v1/market`, admin |
| **Railway Worker (`apps/worker`)** | **Only layer that calls external TCG/market APIs** |
| **Postgres** | `card_identity` (catalog), `sale_event` (comps + listings), `card_price_daily` (rollups) |

**Important:** External clients live in:

- `apps/api/tcgscan_api/sources/` — **admin diagnostics + normalisers** (OPTCG, YGOPRODeck, Bandai probes)
- `apps/worker/tcgscan_worker/sources/` — pricing (eBay, TCGPlayer, Cardmarket)
- `apps/worker/tcgscan_worker/catalog/` — metadata ingest (Pokemon, Scryfall, YGOPRODeck, OPTCG, …)

Background jobs use **Temporal workflows**, not Celery (`apps/worker/tcgscan_worker/workflows/`, `schedules.py`).

---

## Quick answer: Railway env vars you still need

### Worker service (pricing + catalog ingest)

| Priority | Variable | For |
|----------|----------|-----|
| **High** | `EBAY_APP_ID` + `EBAY_CERT_ID` | eBay OAuth (or `EBAY_OAUTH_TOKEN` instead) |
| **High** | `EBAY_MARKETPLACE_ID` | `EBAY_GB` (default) |
| **Recommended** | `EBAY_INSIGHTS_TOKEN` | Real sold comps (without it, sold ingest uses Browse fallback) |
| **Optional** | `POKEMONTCG_API_KEY` | Higher pokemontcg.io rate limits |
| **Medium** | `TCG_API_KEY` | TCGPlayer prices via tcgapi.dev |
| **Optional** | `APIFY_TOKEN` | Cardmarket Apify dataset poll |
| **Optional** | `APIFY_CARDMARKET_DATASET_ID` | Default `cardmarket-trend` |
| **Optional** | `ONE_PIECE_API_BASE_URL` | OPTCG API base (default `https://optcgapi.com`) |
| **Optional** | `DRAGON_BALL_FW_BASE_URL` | Bandai Fusion World card list URL |
| **Optional** | `DRAGON_BALL_MASTERS_BASE_URL` | Bandai Masters card list URL |
| **Not used by code** | `EBAY_DEV_ID` | In `.env.example` only |
| **Not used by code** | `EBAY_AFFILIATE_TRACKING_ID`, `EBAY_AFFILIATE_CAMPAIGN_ID` | EPN not implemented |
| **Not used by code** | `REDDIT_*` | Reddit not implemented |
| **Not used by code** | `CARDMARKET_*`, `APIFY_CARDMARKET_ACTOR_ID` | Official CM / actor runner not implemented |

Worker also needs: `DATABASE_URL`, `TEMPORAL_ADDRESS` (for schedules), same Postgres as API.

### API service

| Variable | Purpose |
|----------|---------|
| `EBAY_MARKETPLACE_ID` | Outbound eBay **search link** host only (no Browse calls) |
| *(optional)* | `TCG_API_KEY`, `APIFY_TOKEN` loaded in config but **not used for live calls** from API |

### Vercel

| Variable | Purpose |
|----------|---------|
| `NEXT_PUBLIC_API_URL` | Railway API base URL |

No external data API keys on Vercel.

---

## Admin diagnostics (new)

Admin-only routes (Bearer + `role` admin+):

| Route | Purpose |
|-------|---------|
| `GET /v1/admin/sources/status` | Env configured flags + ingest paths + DB data-health merge |
| `GET /v1/admin/sources/test/ebay` | OAuth + Browse search probe |
| `GET /v1/admin/sources/test/pokemon` | pokemontcg.io probe |
| `GET /v1/admin/sources/test/scryfall` | Scryfall probe |
| `GET /v1/admin/sources/test/ygopro` | YGOPRODeck probe (no key) |
| `GET /v1/admin/sources/test/one-piece` | OPTCG API probe (no key) |
| `GET /v1/admin/sources/test/dragon-ball-fusion-world` | Bandai FW probe |
| `GET /v1/admin/sources/test/dragon-ball-masters` | Bandai Masters probe |
| `GET /v1/admin/sources/test/reddit` | Reports not implemented |
| `GET /v1/admin/sources/test/cardmarket` | Apify dataset probe |

Admin UI: `/admin/sources` — runs live tests via authenticated SDK (never calls external APIs from browser).

Responses never include secret values — only `status`, `provider`, `message`, and safe sample fields.

Existing: `GET /v1/admin/data-health` — row counts + freshness per `sale_event.source`.

---

## Source-by-source audit

### 1. eBay Browse API

| Item | Detail |
|------|--------|
| **Status** | **Pending approval** — worker coded; production ingest not enabled |
| **Files** | `worker/sources/ebay_auth.py`, `ebay_active.py`, `ebay_sold.py`, `workflows/ebay_workflow.py` |
| **API reads** | `GET /v1/cards/{id}/comps`, `/listings`, `/sources`; `GET /v1/market/sales`, `/listings` |
| **Railway vars** | `EBAY_OAUTH_TOKEN` **or** `EBAY_APP_ID` + `EBAY_CERT_ID`; `EBAY_INSIGHTS_TOKEN`; `EBAY_MARKETPLACE_ID` |
| **Code does NOT read** | `EBAY_DEV_ID`, `EBAY_CLIENT_SECRET`, `EBAY_AFFILIATE_*` |
| **Vercel vars** | None |
| **Provides** | Active listings (`kind=listing`), sold comps (`kind=sold`), raw `itemWebUrl` |
| **Rate limit** | `ResilientClient` 5 req/s burst 10; OAuth token cached |
| **Caching** | Postgres `sale_event`; Temporal 15m active / hourly sold |
| **Test** | `GET /v1/admin/sources/test/ebay`; `uv run pytest apps/worker/tests/test_sources.py -q` |
| **CLI** | `pnpm ingest:pricing -- --source ebay_active` or `ebay_sold` |
| **Missing key** | Source skipped in ingest; search URLs still work from API |
| **Gap** | **Never affiliate-tag outbound links** (product rule violated today); sold without Insights uses Browse active (not true sold data) |

---

### 2. eBay EPN affiliate links

| Item | Detail |
|------|--------|
| **Status** | **Missing** |
| **Files** | Docs only (`CURSOR_CONTEXT.md`, `CLAUDE.md`); `services/marketplace_search.py` builds plain URLs |
| **Expected vars (not wired)** | `EBAY_AFFILIATE_TRACKING_ID`, `EBAY_AFFILIATE_CAMPAIGN_ID` |
| **Provides** | Should wrap `listing_url` + search URLs with EPN params |
| **Failure** | Non-affiliate links (no outage) |

---

### 3. Pokémon TCG API (pokemontcg.io)

| Item | Detail |
|------|--------|
| **Status** | **Working** |
| **Files** | `worker/catalog/pokemon.py`, `catalog/runner.py` |
| **Railway vars** | `POKEMONTCG_API_KEY` (optional) |
| **Vercel vars** | None |
| **Provides** | Name, set, number, rarity, images, legalities, external IDs → `card_identity` |
| **Rate limit** | 4 req/s burst 8; higher with API key |
| **Caching** | Weekly `CatalogIngestWorkflow`; upsert to Postgres |
| **Test** | `GET /v1/admin/sources/test/pokemon`; `pytest apps/worker/tests/test_catalog.py -k pokemon` |
| **CLI** | `pnpm ingest:catalog -- --game pokemon` |
| **Missing key** | Still works; lower rate limit |

---

### 4. Scryfall (MTG)

| Item | Detail |
|------|--------|
| **Status** | **Working** |
| **Files** | `worker/catalog/mtg.py` |
| **Railway vars** | None |
| **User-Agent** | `tcgscan/0.0.0` in client headers |
| **Provides** | Name, set, collector number, rarity, images, Scryfall/TCGPlayer IDs |
| **Rate limit** | 5 req/s burst 10 |
| **Test** | `GET /v1/admin/sources/test/scryfall`; `pytest apps/worker/tests/test_catalog.py -k mtg` |
| **CLI** | `pnpm ingest:catalog -- --game mtg` |

---

### 5. YGOPRODeck (Yu-Gi-Oh)

| Item | Detail |
|------|--------|
| **Status** | **Working** — no API key required |
| **Files** | `apps/api/tcgscan_api/sources/ygoprodeck.py`, `worker/catalog/yugioh.py` |
| **Railway vars** | None (optional `YGOPRODECK_BASE_URL`) |
| **Provides** | Name, type, race, attribute, archetype, level/rank/link, ATK/DEF, sets, images; prices only when API returns `card_prices` |
| **Rate limit** | 2 req/s in API adapter; Redis cache TTL 1h on diagnostic/search |
| **Test** | `GET /v1/admin/sources/test/ygopro` |
| **CLI** | `pnpm ingest:catalog -- --game yugioh` |

---

### 6. One Piece / OPTCG API

| Item | Detail |
|------|--------|
| **Status** | **Working** — no API key required |
| **Files** | `apps/api/tcgscan_api/sources/one_piece.py`, `worker/catalog/one_piece.py` |
| **Railway vars** | Optional `ONE_PIECE_API_BASE_URL` (default `https://optcgapi.com`) |
| **Provides** | Sets, cards, ST/promo/don decks — metadata only; **no fake pricing** |
| **Rate limit** | 4 req/s burst 8; Redis cache TTL 1h |
| **Test** | `GET /v1/admin/sources/test/one-piece` |
| **CLI** | `pnpm ingest:catalog -- --game one_piece` |

---

### 7. Dragon Ball Super Fusion World (Bandai)

| Item | Detail |
|------|--------|
| **Status** | **Not implemented** — official HTML card database only |
| **Files** | `apps/api/tcgscan_api/sources/dragon_ball_fusion_world.py` |
| **Railway vars** | Optional `DRAGON_BALL_FW_BASE_URL` |
| **Provides** | Diagnostic probes JSON candidates; returns `not_implemented` when only HTML exists |
| **Test** | `GET /v1/admin/sources/test/dragon-ball-fusion-world` |
| **Gap** | No aggressive HTML scraping; catalog ingest not wired |

---

### 8. Dragon Ball Super Masters (Bandai)

| Item | Detail |
|------|--------|
| **Status** | **Not implemented** — official HTML card list only |
| **Files** | `apps/api/tcgscan_api/sources/dragon_ball_masters.py` |
| **Railway vars** | Optional `DRAGON_BALL_MASTERS_BASE_URL` |
| **Provides** | Same probe pattern as Fusion World |
| **Test** | `GET /v1/admin/sources/test/dragon-ball-masters` |

---

### 9. Reddit API (sentiment/hype only)

| Item | Detail |
|------|--------|
| **Status** | **Missing** |
| **Files** | None |
| **Expected Railway vars** | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` |
| **Target subreddits (planned)** | `pkmntcg`, `mtgfinance`, `yugioh`, `OnePieceTCG` |
| **Should collect** | Mentions, subreddit, counts, hype score, URL, timestamp → future `trend_signals` table |
| **Test** | `GET /v1/admin/sources/test/reddit` → `implementation: missing` |
| **Failure** | N/A |

---

### 8. Cardmarket / Apify

| Item | Detail |
|------|--------|
| **Status** | **Partial** — Apify dataset poll only |
| **Files** | `worker/sources/cardmarket.py`; API search URLs in `services/marketplace_search.py` |
| **Railway vars (used)** | `APIFY_TOKEN`, `APIFY_CARDMARKET_DATASET_ID` |
| **Railway vars (not used)** | `APIFY_CARDMARKET_ACTOR_ID`, `CARDMARKET_APP_TOKEN`, `CARDMARKET_APP_SECRET`, `CARDMARKET_ACCESS_TOKEN`, `CARDMARKET_ACCESS_TOKEN_SECRET` |
| **Provides** | EU trend/price rows → `sale_event` (EUR → USD via `fx_rate`) |
| **Rate limit** | 1 req/s |
| **Default** | Disabled when `APIFY_TOKEN` absent |
| **Test** | `GET /v1/admin/sources/test/cardmarket` |
| **CLI** | `pnpm ingest:pricing -- --source cardmarket` |
| **Gap** | No Apify actor trigger; dataset must exist externally |

---

### Bonus: TCGPlayer (tcgapi.dev)

| Item | Detail |
|------|--------|
| **Status** | **Working** |
| **Files** | `worker/sources/tcgplayer.py` |
| **Railway vars** | `TCG_API_KEY` |
| **Provides** | TCGPlayer market prices → `sale_event` |
| **CLI** | `pnpm ingest:pricing -- --source tcgplayer` |

---

## API routes (read DB only)

| Route | Data |
|-------|------|
| `GET /v1/cards/search` | `card_identity` |
| `GET /v1/cards/{id}` | Card detail |
| `GET /v1/cards/{id}/comps` | `sale_event` sold comps |
| `GET /v1/cards/{id}/listings` | `sale_event` listings |
| `GET /v1/cards/{id}/sources` | Aggregated source medians + search URLs |
| `GET /v1/cards/{id}/chart` | `card_price_daily` |
| `GET /v1/market/sales` | Browse sold comps |
| `GET /v1/market/listings` | Browse listings |
| `GET /v1/market/movers` | Computed from `sale_event` |
| `GET /v1/market/fx` | `fx_rate` table |
| `GET /v1/market/indexes` | Index summaries |

Price/value computation: `SalesRepo.rollup_day()` (worker `rollup.py` + `RollupWorkflow` daily).

---

## Data model audit

| Requested table | Actual | Notes |
|-----------------|--------|-------|
| `cards` | `card_identity` | Canonical catalog |
| `card_sets` | *(missing)* | Denormalised on `card_identity` |
| `price_observations` | *(missing)* | Raw → `sale_event`; aggregates → `card_price_daily` |
| `marketplace_listings` | *(missing)* | `sale_event` where `kind='listing'` |
| `trend_signals` | *(missing)* | Movers computed at query time; Reddit not stored |
| `source_runs` | *(missing)* | Use `/v1/admin/data-health` until migration |
| Subscriptions | `users.tier`, `users.stripe_customer_id` | No `subscription_status` column yet |

**Proposed before live Reddit/EPN:** `0010_source_runs`, `0011_trend_signals` — document only, not applied.

---

## Background jobs (Temporal, not Celery)

| Job | Schedule | Module |
|-----|----------|--------|
| eBay active | 15 min | `EbayActiveWorkflow` |
| eBay sold | 1 hour | `EbaySoldWorkflow` |
| TCGPlayer + Cardmarket pricing | Daily | `MarketplacePricingWorkflow` |
| Price rollups | Daily | `RollupWorkflow` |
| Catalog per game | Weekly | `CatalogIngestWorkflow` × 6 games |
| Alert monitor | 15 min | `AlertMonitorWorkflow` |
| Digest | 24 h | `DigestWorkflow` |

Register schedules: `pnpm worker schedules:register` (requires Temporal + approval for prod).

**Missing / to add later:**

- Reddit trend ingest workflow
- EPN URL rewrite post-ingest
- Apify actor trigger for Cardmarket
- `source_runs` audit logging
- Long-tail eBay schedule (6h) mentioned in docs but not in `schedules.py`

---

## Source strategy (target)

| Role | Source | Status |
|------|--------|--------|
| Pokémon metadata | pokemontcg.io | ✅ Worker catalog |
| MTG metadata | Scryfall | ✅ Worker catalog |
| Yu-Gi-Oh metadata | YGOPRODeck (no key) | ✅ API adapter + worker catalog |
| One Piece metadata | OPTCG API (no key) | ✅ API adapter + worker catalog |
| Dragon Ball FW metadata | Bandai official DB | ❌ HTML only — adapter not implemented |
| Dragon Ball Masters metadata | Bandai official list | ❌ HTML only — adapter not implemented |
| Live listings + comps | eBay Browse (+ Insights) | ⏸ Pending approval; no EPN |
| US TCG prices | tcgapi.dev | ✅ Worker pricing |
| EU prices | Cardmarket via Apify | ⚠️ Dataset poll only |
| Community hype | Reddit | ❌ Not built |

**Pricing rule:** Catalog metadata sources do not provide live market prices unless the upstream API explicitly includes them (e.g. YGOPRODeck `card_prices`). Live comps come later from eBay, Cardmarket, and paid APIs.

---

## Dragon Ball + One Piece ingest plan

| Game | Source | Ingest status |
|------|--------|---------------|
| One Piece | OPTCG API (`ONE_PIECE_API_BASE_URL`) | **Candidate** — worker `one_piece` catalog exists; no huge automatic prod imports yet |
| Dragon Ball Fusion World | Bandai official card database | **Blocked** — no clean JSON endpoint; probe returns `not_implemented` |
| Dragon Ball Masters | Bandai official card list | **Blocked** — same as Fusion World |

**Future worker tasks (Temporal, not yet implemented):**

- `refresh_one_piece_catalogue` — upsert by `(game, source, source_card_id)`
- `refresh_dragon_ball_fw_catalogue` — after JSON adapter or approved Bandai integration
- `refresh_dragon_ball_masters_catalogue` — same

**Operational rules:**

- Store `source_runs` status per ingest (table not migrated yet — use `/v1/admin/data-health` interim)
- Upsert key: `game + source + source_card_id`
- No full-catalog prod imports without explicit approval
- Pricing ingest remains separate (eBay / Cardmarket / TCGPlayer)

---

## Verification commands

```bash
# Admin status (requires admin Bearer token)
curl -H "Authorization: Bearer $TOKEN" \
  https://tcg-scan-web-app-production.up.railway.app/v1/admin/sources/status

# Worker unit tests
uv run pytest apps/worker/tests/test_catalog.py -q
uv run pytest apps/worker/tests/test_sources.py -q
uv run pytest apps/worker/tests/test_pricing_ingest.py -q

# API tests
uv run pytest apps/api -q

# Manual ingest (worker service, staging DB first)
pnpm ingest:catalog -- --game pokemon --limit 10
pnpm ingest:pricing -- --game pokemon --card-limit 5
```

---

## Implementation priority (next PRs)

1. **EPN affiliate helper** — wrap stored `listing_url` + search URLs (worker on ingest + API on read)
2. **eBay Insights token** — Railway `EBAY_INSIGHTS_TOKEN` for accurate sold comps
3. **Worker Railway service** — deploy with eBay + TCG + optional Apify keys; run ingest
4. **Reddit adapter + `trend_signals` migration** — hype only
5. **`source_runs` table** — ingest audit trail

---

*See also:* `docs/LIVE_DATA_AND_STRIPE_SETUP.md` (Stripe + earlier env checklist).
