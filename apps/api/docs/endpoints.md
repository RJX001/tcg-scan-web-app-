# API endpoints

Canonical list for `apps/api`. Regenerate SDK after changes: `pnpm sdk:generate`.

| Method | Path | Auth | Cache | Purpose |
|---|---|---|---|---|
| GET | `/v1/health` | public | — | Liveness probe |
| POST | `/v1/scan` | optional | Redis `scan:{sha256}` 24h | Multipart image → top-K matches + condition + bbox + `stages_ms` |
| GET | `/v1/cards/search` | public | — | Text search by name, set, number |
| GET | `/v1/cards/slug/{slug}` | public | Redis `cards:slug:{slug}` 900s | Card detail by SEO slug |
| GET | `/v1/cards/{id}` | public | Redis `cards:{id}` 900s | Card detail by UUID |
| GET | `/v1/cards/{id}/comps` | public | — | Sold comps (filterable by source, grade) |
| GET | `/v1/cards/{id}/comps/summary` | public | — | Mean/median/min/max comp stats |
| GET | `/v1/cards/{id}/comps/summary/by-grade` | public | — | Comp stats broken out by grade bucket |
| GET | `/v1/cards/{id}/listings` | public | — | Active marketplace listings |
| GET | `/v1/cards/{id}/chart` | public | — | Daily price roll-ups for chart |
| GET | `/v1/cards/{id}/sources` | public | — | Cross-marketplace median tiles (eBay, TCGPlayer, Cardmarket) |
| GET | `/v1/cards/{id}/grade-roi` | public | — | HOLD / SELL / GRADE verdict (GradeROIAgent + comps) |
| GET | `/v1/market/movers` | public (`pop` sort: Pro) | Redis `market:movers:*` 300s | Ladder: ranked cards with last sold, sales volume, % change over `days` window, graded pop (sort: change, change_asc, price, volume, recent, market_cap, pop) |
| GET | `/v1/market/listings` | public | Redis `market:listings:*` 300s | Shop: cross-catalog active listings (filter: game, q, source, grade, min/max price, listed_after/before; sort: recent, price_asc, price_desc) |
| GET | `/v1/market/sales` | public | Redis `market:sales:*` 300s | Sales: global sold-comps browse (filter: game, q, source, grade, min/max price, sold_after/before; sort: recent, price_asc, price_desc) |
| GET | `/v1/market/indexes` | public | Redis `market:indexes:*` 900s | All composite indexes with % change over `days` window (Indexes tab) |
| GET | `/v1/market/index` | public | Redis `market:index:*` 900s | Composite market index (CL50-style): equal-weighted, rebased to 100 at window start; optional `game` filter |
| GET | `/v1/market/fx` | public | Redis `market:fx` 3600s | Latest FX rates (base USD, `rate_to_usd` per currency) for client-side display conversion |
| GET | `/v1/watchlist` | authed | — | List watchlist items with 30d median |
| POST | `/v1/watchlist` | authed + Pro | — | Watch a card (idempotent) |
| DELETE | `/v1/watchlist/{item_id}` | authed | — | Remove watchlist item |
| GET | `/v1/cards/{id}/population` | public | — | Graded population per company + grade (PSA/BGS/CGC snapshots) |
| GET | `/v1/searches` | authed | — | List saved ladder searches |
| POST | `/v1/searches` | authed + Pro | — | Create/replace saved search (upsert by name) |
| DELETE | `/v1/searches/{search_id}` | authed | — | Delete saved search |
| GET | `/v1/portfolio` | authed | — | List portfolio items with estimated value |
| GET | `/v1/portfolio/summary` | authed | — | Collection totals |
| GET | `/v1/portfolio/export` | authed | — | CSV export (tax-ready) |
| POST | `/v1/portfolio` | authed | — | Add or increment portfolio item (Free tier limit enforced) |
| DELETE | `/v1/portfolio/{item_id}` | authed | — | Remove portfolio item |
| GET | `/v1/alerts` | authed | — | List price alerts |
| POST | `/v1/alerts` | authed + Pro | — | Create price alert |
| DELETE | `/v1/alerts/{alert_id}` | authed | — | Delete price alert |
| GET | `/v1/account` | authed | — | Tier, limits, email |
| POST | `/v1/billing/checkout` | authed | — | Stripe Checkout session (Pro upgrade) |
| POST | `/v1/billing/portal` | authed | — | Stripe Customer Portal |
| POST | `/v1/billing/webhook` | Stripe sig | — | Tier sync from Stripe events |
| GET | `/v1/digest/preview` | authed + Pro | — | Daily brief preview (DigestAgent) |

**Dev auth:** `DEV_AUTH_ENABLED=true` → header `X-Dev-User-Id: dev-user`.

**Rate limits:** Free tier scan quota via Redis token bucket (`FREE_SCANS_PER_DAY`).
