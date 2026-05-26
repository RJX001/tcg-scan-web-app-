# Data sources — TCG Scan Phase 1 (Weeks 1–5)

Canonical reference for catalog ingestors and pricing workers. See `AGENTS.md` §5 for ingestion rules.

## Catalog sources

| Game slug | Source | Auth | Rate limit | Module |
|---|---|---|---|---|
| `pokemon` | [pokemontcg.io](https://pokemontcg.io) | Optional `POKEMONTCG_API_KEY` | 20 req/s with key | `catalog/pokemon.py` |
| `mtg` | [Scryfall](https://scryfall.com/docs/api) | None | 10 req/s | `catalog/mtg.py` |
| `yugioh` | [YGOPRODeck](https://ygoprodeck.com/api-guide/) | None | 2 req/s | `catalog/yugioh.py` |
| `lorcana` | [Lorcast](https://lorcast.com) | None | 2 req/s | `catalog/lorcana.py` |
| `one_piece` | [optcgapi.com](https://optcgapi.com) | None | 2 req/s | `catalog/one_piece.py` |
| `sports` | [tcgapi.dev](https://tcgapi.dev) sports | `TCG_API_KEY` | 3 req/s | `catalog/sports.py` |

**CLI:** `pnpm ingest:catalog -- --game pokemon [--limit N]`

**Temporal:** Weekly `CatalogIngestWorkflow` per game (see `schedules.py`).

## Pricing sources

| Source ID | Marketplace | Method | Auth | Schedule | Module |
|---|---|---|---|---|---|
| `ebay_active` | eBay US active listings | Official Browse API | `EBAY_OAUTH_TOKEN` or client-credentials | Every 15 min (top 1k) | `sources/ebay_active.py` |
| `ebay_sold` | eBay sold comps | Marketplace Insights (preferred) or Browse fallback | `EBAY_INSIGHTS_TOKEN` or OAuth | Hourly (top 10k) | `sources/ebay_sold.py` |
| `tcgplayer` | TCGPlayer market prices | tcgapi.dev proxy | `TCG_API_KEY` | Daily | `sources/tcgplayer.py` |
| `cardmarket` | Cardmarket EU trends | Apify dataset poll | `APIFY_TOKEN`, `APIFY_CARDMARKET_DATASET_ID` | Daily | `sources/cardmarket.py` |

**CLI:** `pnpm ingest:pricing -- --game pokemon --card-limit 1000`

**Default sources:** eBay sold + active, TCGPlayer, Cardmarket (all normalised to `sale_event`).

## FX normalization

Non-USD comps (Cardmarket EUR) are converted via `fx_rate` table. Dev defaults in `pricing/fx.py`; production should fetch daily ECB rates.

## Legal / ToS notes

- Prefer official APIs where available (eBay Browse, Scryfall, pokemontcg.io).
- eBay Marketplace Insights requires limited-release approval — apply Day 1; Browse fallback documented in `ebay_sold.py`.
- Cardmarket official API is closed to new apps — Apify scraper with aggressive caching only.
- Sports catalog via paid TCG API tier — budget $10–100/mo per Phase 1 plan.

## Environment variables

See `.env.example` for the full list. Minimum for Weeks 2–5 local dev:

```bash
DATABASE_URL=postgresql+asyncpg://tcgscan:tcgscan@localhost:5432/tcgscan
QDRANT_URL=http://localhost:6333
REDIS_URL=redis://localhost:6379
TEMPORAL_ADDRESS=localhost:7233
# Optional for live pricing:
EBAY_OAUTH_TOKEN=
TCG_API_KEY=
APIFY_TOKEN=
```
