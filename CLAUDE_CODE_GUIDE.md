# OBSOLETE — DO NOT USE

> This guide targets an abandoned `backend/` + Celery + Poetry scaffold and Sprint 1 paths that **do not exist** in the current monorepo.
>
> Use **`AGENTS.md`**, **`CLAUDE.md`**, and **`README.md`** for setup. Product intent: **`docs/TCG_Scan_Phase1.md`**.

---

# Running TCG Scan Phase 1 with Claude Code (ARCHIVED)

## Step 1 — Install Claude Code

You need Node.js 18+ installed first. Then run:

```bash
npm install -g @anthropic-ai/claude-code@latest
```

Verify it worked:
```bash
claude --version
```

Then authenticate with your Anthropic account (needs Claude Pro or API credits):
```bash
claude auth login
```

---

## Step 2 — Unzip and open the project

```bash
# Unzip the scaffold
unzip tcg-scan-phase-1.zip
cd tcg-scan-phase-1

# Launch Claude Code inside the project folder
claude
```

Claude Code will automatically read `CLAUDE.md` at the start of every session.
This gives it your commands, architecture, constraints, and Sprint 1 instructions.
You never need to drag or attach files — it reads CLAUDE.md automatically.

---

## Step 3 — First session commands (Sprint 1)

Once Claude Code is running, paste these one at a time:

### Command 1 — Environment setup
```
Set up the backend environment:
1. Install dependencies with poetry install
2. Copy .env.example to .env
3. Generate a secure 64-character SECRET_KEY and add it to .env
4. Run docker compose up -d and wait for postgres, pgbouncer, and redis to be healthy
5. Run poetry run alembic upgrade head to create all tables and seed data
6. Confirm: all 14 tables exist, 5 games seeded, 17 grades seeded
Report status of each step.
```

### Command 2 — Pokémon catalogue
```
Implement PokemonTcgIOClient.fetch_all_cards() in backend/app/sources/catalogue/__init__.py.

Use the Pokémon TCG IO API at https://api.pokemontcg.io/v2/cards (paginated, no key needed).
Extract: id, name, number, set.name, set.id, set.releaseDate, rarity, images.large
Map to our Card + Set models. Create set if not exists, then create card.
Target: all English sets from Base Set onwards.

Write a pytest test that mocks the API and confirms cards are returned correctly.
Run the test.
```

### Command 3 — MTG + YGO catalogues
```
Implement ScryfallClient.fetch_all_cards() and YgoProDeckClient.fetch_all_cards()
in backend/app/sources/catalogue/__init__.py.

Scryfall: https://api.scryfall.com/cards/search?q=is:paper&unique=prints
  - Rate limit 100ms between requests
  - Fields: id, name, set, set_name, collector_number, rarity, image_uris.large, released_at

YGOPRODECK: https://db.ygoprodeck.com/api/v7/cardinfo.php (single call, no pagination)
  - Fields: id, name, card_sets (set_name, set_code, set_rarity), card_images[0].image_url

Run both. Report total cards seeded per game.
```

### Command 4 — eBay Browse API
```
Implement EbaySource.ingest_recent_sales() in backend/app/sources/ebay/__init__.py.

Use the eBay Browse API (official, not scraping).
Read EBAY_APP_ID from settings. Implement OAuth client_credentials token flow.
Query sold listings for Pokémon TCG (category ID 183454).
For each result: match title to card in our DB via fuzzy search, create card_sale record.
Extract: sale_price, currency, sale_date, source_url.
Detect grade from title if present (PSA 9, BGS 10, Raw etc).

ALL buy links must go through EbaySource.build_affiliate_url() — never return a raw eBay URL.

Write a test. Run it.
```

### Command 5 — TCG Value computation
```
Implement compute_tcg_values() in backend/app/tasks/compute_values.py.

For each card_id + grade_id pair with >= 5 sales in the last 90 days:
  - Compute median sale_price (exclude top/bottom 10% as outliers)
  - Upsert into card_values table

Cards with fewer than 5 sales must NOT get a card_values row.
The UI will show "Insufficient data" for those cards.

Schedule this task to run nightly at 02:00 UTC via Celery beat.
Write a test for the calculation logic.
```

### Command 6 — Sprint 1 completion check
```
Sprint 1 completion check. Verify each item and tell me pass/fail:

1. docker compose ps — postgres, pgbouncer, redis all Up
2. alembic current — shows 001_initial as head
3. All 14 tables exist in the database
4. Pokémon catalogue: at least 10,000 cards seeded
5. MTG catalogue: at least 5,000 cards seeded
6. YGO catalogue: at least 5,000 cards seeded
7. At least 100 card_sales records after running eBay scraper
8. card_values populated for cards with >= 5 sales
9. Celery beat schedule registered for compute_tcg_values at 2 AM UTC
10. pytest -x passes with no failures
11. No .env secrets committed to git

Fix any failures before we call Sprint 1 done.
```

---

## Useful Claude Code commands

| Command | What it does |
|---|---|
| `/memory` | See what Claude has learned about your project |
| `/permissions` | View and manage what Claude can do |
| `/init` | Regenerate CLAUDE.md suggestions from codebase |
| `Ctrl+C` | Interrupt Claude if it goes off track |
| `Esc` | Cancel current action |

---

## Sprint 2 onwards — same pattern

Start each new sprint with:
```
We are starting Sprint 2: Core API & Search.

Task: Implement CardRepository.search() in backend/app/repositories/cards.py
using PostgreSQL tsvector full-text search on card name + set name.
Wire it to the /api/v1/cards route handler.
Write tests for search(), get_by_id(), and get_values().
```

The full sprint map is in CURSOR_CONTEXT.md for reference.

---

## If something breaks

```
Something broke. Read the full error.
Check CLAUDE.md architecture rules — is this a violation?
Fix at root cause, not the symptom.
Run pytest after fixing.
Tell me: what caused it, what you changed, test result.
```

---

## Claude Code vs Cursor — which to use

| Task | Use |
|---|---|
| Architecture decisions, complex design | Claude Pro (here, this chat) |
| Sprint-by-sprint implementation | Claude Code (terminal) |
| Autocomplete while writing code | Cursor with claude-sonnet-4-6 |
| Complex maths (cost basis etc) | ChatGPT Pro o3 |

Claude Code is best for: "implement this whole feature end to end, run the tests, fix failures."
Cursor is best for: autocomplete and quick edits while you are inside a file.
