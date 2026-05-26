// Builds TCG_Scan_Phase1.docx
const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, HeadingLevel, LevelFormat, BorderStyle, WidthType,
  ShadingType, PageBreak, ExternalHyperlink, TableOfContents, PageNumber,
  Header, Footer, TabStopType, TabStopPosition,
} = require('docx');

// ---------- helpers ----------
const PAGE_W = 12240;
const PAGE_H = 15840;
const MARGIN = 1080; // 0.75"
const CONTENT_W = PAGE_W - MARGIN * 2; // 10080

const border = { style: BorderStyle.SINGLE, size: 4, color: 'BFBFBF' };
const borders = { top: border, bottom: border, left: border, right: border };
const cellMargins = { top: 80, bottom: 80, left: 120, right: 120 };

const t = (text, opts = {}) => new TextRun({ text, font: 'Calibri', ...opts });

const para = (children, opts = {}) =>
  new Paragraph({ children: Array.isArray(children) ? children : [children], spacing: { after: 120 }, ...opts });

const p = (text, opts = {}) =>
  para([t(text)], opts);

const h1 = (text) =>
  new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children: [new TextRun({ text, font: 'Calibri', bold: true, color: '0F3D7A', size: 32 })],
    spacing: { before: 360, after: 180 },
  });

const h2 = (text) =>
  new Paragraph({
    heading: HeadingLevel.HEADING_2,
    children: [new TextRun({ text, font: 'Calibri', bold: true, color: '1F4E79', size: 26 })],
    spacing: { before: 240, after: 120 },
  });

const h3 = (text) =>
  new Paragraph({
    heading: HeadingLevel.HEADING_3,
    children: [new TextRun({ text, font: 'Calibri', bold: true, color: '2E75B6', size: 22 })],
    spacing: { before: 200, after: 100 },
  });

const bullet = (text) =>
  new Paragraph({
    numbering: { reference: 'bullets', level: 0 },
    children: [t(text)],
    spacing: { after: 80 },
  });

const bulletRich = (runs) =>
  new Paragraph({
    numbering: { reference: 'bullets', level: 0 },
    children: runs,
    spacing: { after: 80 },
  });

const num = (text) =>
  new Paragraph({
    numbering: { reference: 'numbers', level: 0 },
    children: [t(text)],
    spacing: { after: 80 },
  });

function table(headers, rows, widths) {
  const total = widths.reduce((a, b) => a + b, 0);
  const headerRow = new TableRow({
    tableHeader: true,
    children: headers.map((h, i) => new TableCell({
      borders,
      width: { size: widths[i], type: WidthType.DXA },
      shading: { fill: '1F4E79', type: ShadingType.CLEAR },
      margins: cellMargins,
      children: [new Paragraph({ children: [new TextRun({ text: h, font: 'Calibri', bold: true, color: 'FFFFFF' })] })],
    })),
  });
  const bodyRows = rows.map((row, ri) => new TableRow({
    children: row.map((cell, i) => new TableCell({
      borders,
      width: { size: widths[i], type: WidthType.DXA },
      shading: { fill: ri % 2 ? 'F2F2F2' : 'FFFFFF', type: ShadingType.CLEAR },
      margins: cellMargins,
      children: [new Paragraph({ children: [new TextRun({ text: String(cell), font: 'Calibri', size: 20 })] })],
    })),
  }));
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: widths,
    rows: [headerRow, ...bodyRows],
  });
}

const link = (text, url) =>
  new ExternalHyperlink({
    children: [new TextRun({ text, font: 'Calibri', style: 'Hyperlink', color: '2E75B6' })],
    link: url,
  });

// ---------- content ----------
const children = [];

// Cover
children.push(new Paragraph({
  spacing: { before: 2400, after: 240 },
  alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: 'TCG Scan', font: 'Calibri', bold: true, size: 72, color: '0F3D7A' })],
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 120 },
  children: [new TextRun({ text: 'Phase 1 Plan — v1.0', font: 'Calibri', size: 36, color: '1F4E79' })],
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 480 },
  children: [new TextRun({ text: 'AI-Native Price Intelligence for Every Trading Card', font: 'Calibri', italics: true, size: 26, color: '595959' })],
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 120 },
  children: [new TextRun({ text: 'Prepared for: RJ — Founder, AI/ML Engineer', font: 'Calibri', size: 22 })],
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 120 },
  children: [new TextRun({ text: 'Date: May 2026', font: 'Calibri', size: 22 })],
}));
children.push(new Paragraph({ children: [new PageBreak()] }));

// 0 TL;DR
children.push(h1('0. Executive Summary'));
children.push(p('TCG Scan v1 is a universal price-intelligence platform for trading cards — web app first, mobile second, sharing a single backend. The core promise: take a photo of any card and instantly see the last 30 days of sold prices on eBay, TCGPlayer, Cardmarket, every active listing, plus an AI condition and grading ROI verdict.'));
children.push(p('We win against 130point and Card Ladder by being:'));
children.push(num('Multi-TCG plus sports in one app (they are sports-only or TCG-shallow).'));
children.push(num('AI-native scan-first UX (130point’s scan is bolted on, Card Ladder has no AI scan).'));
children.push(num('Cross-marketplace by default — eBay sold, TCGPlayer, Cardmarket (EU), and auction houses, deduplicated in one card view.'));
children.push(num('Agentic price intelligence — autonomous watchers, alerts, arbitrage, anomaly and shill detection.'));
children.push(num('Portfolio plus grading ROI in one place — what Card Ladder is openly missing.'));
children.push(p('Build approach: solo full-stack ML engineer plus heavy agentic coding (Cursor 2.4 subagents, Claude Code with subagents, LangGraph for production ML and agent workflows).'));

// 1 Market & Competitor Audit
children.push(h1('1. Market & Competitor Audit'));
children.push(h2('1.1 Direct competitors'));
children.push(table(
  ['Competitor', 'Strength', 'Weakness we exploit'],
  [
    ['130point.com', 'Free; aggregates 8+ marketplaces (eBay, PWCC, Goldin, Heritage, MySlabs, Pristine); 15M+ sold items; mobile app', 'Sports-only focus; search-tool UX (no real portfolio); shallow TCG support; no AI condition grading; no agentic alerts'],
    ['Card Ladder', 'Cleanest UI; sales back to 2000; portfolio tracker; Card Ladder Index; daily email; Pro tier', 'Sports-only; no AI scan; no grading ROI; no dealer tools; "charts without actionable intelligence"'],
    ['Market Movers (SCI)', '2M+ cards (sports + TCG + non-sports); price alerts; 25-item free tier', 'Limited free tier; weaker scan UX; not camera-first'],
    ['Slabfy', 'Dealer ops (POS, consignment, Flip Finder, grade-ladder ROI)', 'Dealer/business focus; expensive; sports-leaning'],
    ['Ludex', 'Strong analytics + portfolio; $7.99/mo; sports + TCG', 'Niche split per category; dated UI'],
    ['Collectr', 'Pokemon-collector loved; clean UI; live auctions', 'Slow/less reliable scanner; Pokemon-leaning'],
    ['CardPriceIQ', 'Claimed 94% scan accuracy across Pokemon/MTG/Sports; 20+ price sources', 'Smaller brand; weaker portfolio'],
    ['Eyevo', 'Pokemon-only; <1s scan, 95%+ claim', 'Pokemon-only'],
    ['TCG Radar', 'Computer-vision condition assessment', 'Narrow audience'],
    ['TCGplayer official', 'Marketplace-integrated scan; canonical TCG catalog', 'Closed ecosystem; eBay-owned; biased to TCGPlayer prices'],
    ['PriceCharting', 'Sealed product pricing', 'Cards weaker than competitors'],
  ],
  [1900, 4090, 4090]
));

children.push(h2('1.2 Gaps in the market (our wedge)'));
children.push(bullet('No single product serves all latest TCGs (Pokemon, MTG, Yu-Gi-Oh, One Piece, Lorcana, Star Wars Unlimited, Flesh & Blood, Digimon, Weiss Schwarz, Union Arena) AND sports cards under one roof with a quality AI scanner.'));
children.push(bullet('No competitor reliably surfaces 30-day eBay sold + TCGPlayer last sold + Cardmarket EU trend + active listings in one card detail view.'));
children.push(bullet('No mainstream competitor uses agentic AI workflows (LangGraph / Claude / multi-agent) for autonomous price monitoring, arbitrage, and grading recommendations.'));
children.push(bullet('Card Ladder, the UX leader, openly lacks AI verdicts and grading ROI — direct opening.'));

children.push(h2('1.3 Positioning'));
children.push(para([new TextRun({ text: 'TCG Scan is the AI-native price intelligence platform for every modern card game and sports card — scan once, get the last 30 days of real sales, current listings, condition grade, and an AI verdict on whether to hold, sell, or grade.', font: 'Calibri', italics: true })]));

// 2 Phase 1 Scope
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h1('2. Phase 1 Product Scope (v1)'));
children.push(p('Phase 1 ships a web app fully usable on desktop and mobile browsers, with a mobile-optimised PWA + camera scan flow, backed by a single API and ML platform that the future native app will also consume.'));

children.push(h2('2.1 v1 must-haves'));
const musts = [
  'Universal card catalog: Pokemon, MTG, Yu-Gi-Oh, One Piece, Lorcana, Star Wars Unlimited, Flesh & Blood, Digimon, Weiss Schwarz, Union Arena, plus sports cards (baseball, basketball, football, soccer, F1, UFC). Unified card_identity schema across games.',
  'Card scan from photo: web upload OR webcam capture. Returns top-K matches with confidence. Two-stage pipeline: detection → embedding ANN search → OCR re-rank.',
  'Card detail page: last 30-day eBay sold comps (mean/median/min/max, raw vs graded), current eBay active listings, TCGPlayer market + low/mid/high, Cardmarket trend + EU low, auction house results, 90-day chart, PSA/BGS/CGC links and grade-ladder ROI estimate.',
  'AI condition assessment: estimated PSA grade range (e.g. 8–9) plus subgrades (centering, corners, edges, surface).',
  'Portfolio: add cards, auto-valued daily, daily-change chart, CSV / tax-ready export.',
  'Price alerts: drop-below / spike-above / PSA 10 comp above threshold.',
  'Search: type-to-search (name, set, number) plus image-search.',
  'Auth + payments: free tier (10 scans/day, no alerts), Pro tier (unlimited scans, alerts, portfolio analytics).',
];
musts.forEach((m, i) => children.push(num(m)));

children.push(h2('2.2 v1 stretch'));
children.push(bullet('Agentic Daily Brief — Claude-generated portfolio + market digest.'));
children.push(bullet('Flip Finder — real-time arbitrage watcher.'));
children.push(bullet('Counterfeit / shill-bid heuristic flag.'));

children.push(h2('2.3 v1 non-goals'));
children.push(bullet('Native iOS/Android apps (Phase 2).'));
children.push(bullet('Live auctions / in-app marketplace (Phase 3).'));
children.push(bullet('P2P trading (Phase 3).'));
children.push(bullet('Sealed product / wax tracking (Phase 2).'));
children.push(bullet('Multilingual UI (English-only at launch).'));

// 3 Architecture
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h1('3. System Architecture'));

children.push(h2('3.1 Topology'));
children.push(p('Client tier (Next.js web; React Native mobile in Phase 2) → Edge API (Next.js route handlers + Hono) → FastAPI core API + LangGraph agent orchestrator → Postgres (Supabase, pgvector), Qdrant (image embeddings), Redis (cache + queue), Cloudflare R2 (image storage) → Modal-hosted GPU ML platform (detection, embedding, OCR, grading) → Temporal / Celery data-ingestion workers pulling eBay, TCGPlayer, Cardmarket, auction houses, and catalogs.'));

children.push(h2('3.2 Tech stack'));
children.push(table(
  ['Layer', 'Choice', 'Why'],
  [
    ['Web framework', 'Next.js 15 (App Router) + TypeScript', 'SSR/RSC for SEO on card pages; mature; Vercel-native'],
    ['UI', 'Tailwind + shadcn/ui + lucide-react', 'Fast, consistent, AI-friendly to scaffold'],
    ['Charts', 'Recharts + Lightweight Charts', 'Industry standard'],
    ['Mobile (Phase 2)', 'React Native + Expo', 'Share TS types / SDK with web'],
    ['Backend', 'FastAPI (Python 3.12) + Pydantic v2', 'Plays with ML stack; Python/ML native'],
    ['Auth', 'Clerk', 'Fast setup, orgs for future dealer tier'],
    ['DB (OLTP)', 'PostgreSQL 16 via Supabase', 'Free tier; pgvector built in'],
    ['Vector DB (images)', 'Qdrant Cloud or self-hosted', 'Rust, fast, payload filtering'],
    ['Cache / queue', 'Redis (Upstash)', 'Serverless, free tier'],
    ['Workflow / agents', 'LangGraph + Claude (Sonnet 4.6 + Haiku 4.5)', 'Production agentic; LangSmith traces'],
    ['Workers', 'Temporal Cloud or Celery', 'Durable executions for price watchers'],
    ['ML serving', 'Modal.com', 'GPU pay-per-second; deploys from Python'],
    ['Object storage', 'Cloudflare R2', 'S3 compatible, no egress fees'],
    ['Payments', 'Stripe', 'Standard'],
    ['Observability', 'OpenTelemetry → Grafana Cloud, LangSmith, Sentry', 'Production-grade'],
    ['Monorepo', 'Turborepo + pnpm', 'First-class Next.js + RN + shared TS'],
  ],
  [1700, 3600, 4780]
));

children.push(h2('3.3 Repo layout'));
children.push(p('Turborepo monorepo with apps/ (web, api, worker, ml) and packages/ (sdk-ts, sdk-py, ui, schema, agents). AGENTS.md per package so Cursor subagents pick up local conventions; root CLAUDE.md mirrors §3 of this plan.'));

// 4 Data
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h1('4. Data Strategy'));

children.push(h2('4.1 Card identity catalog'));
children.push(table(
  ['Game', 'Source', 'Notes'],
  [
    ['Pokemon', 'pokemontcg.io', 'Free; includes images + sets'],
    ['Magic: The Gathering', 'Scryfall', 'Free; gold standard; includes prices'],
    ['Yu-Gi-Oh', 'YGOPRODeck', 'Free'],
    ['One Piece', 'one-piece-cardgame.dev / community', 'Community'],
    ['Lorcana', 'lorcast.com', 'Free'],
    ['Star Wars Unlimited', 'swudb.com', 'Community'],
    ['Flesh & Blood', 'fabdb.net', 'Community'],
    ['Digimon', 'digimoncard.io', 'Community'],
    ['Sports', 'Custom ingest (TCG API / TCGAPIs / scraped)', 'Paid tier later'],
  ],
  [2200, 4600, 3280]
));

children.push(h2('4.2 Pricing ingestion'));
children.push(table(
  ['Source', 'Method', 'Status / cost', 'Fallback'],
  [
    ['eBay Browse API (active)', 'Official, public', 'Approved on signup', 'n/a'],
    ['eBay Marketplace Insights (90d sold)', 'Official, limited release — apply Day 1', 'May take weeks', 'Browse + completed-listings scraper'],
    ['TCGPlayer', 'TCG API.dev / TCGAPIs.com', '$10–$100/mo', 'Scryfall passthrough (MTG)'],
    ['Cardmarket (EU)', 'Apify scrapers / Poketrace', 'Apify pay-per-run', 'Manual scrape'],
    ['Heritage / PWCC / Goldin / MySlabs', 'Scheduled scrape', 'Reasonable; mind ToS', 'n/a'],
    ['Scryfall / pokemontcg.io price hints', 'Free APIs', 'Free', 'n/a'],
  ],
  [2200, 2800, 2540, 2540]
));

children.push(h2('4.3 Freshness SLOs'));
children.push(bullet('Active eBay listings: refresh popular cards every 15 min, long-tail every 6h.'));
children.push(bullet('Sold comps: hourly polling on top 10k cards, daily on the rest.'));
children.push(bullet('Catalog: full refresh weekly; on-demand for new sets.'));

// 5 AI/ML
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h1('5. AI / ML Pipelines'));

children.push(h2('5.1 Card scan pipeline (target p95 < 2.5s on web)'));
const pipeline = [
  'Detection — YOLOv11-nano fine-tuned on cards (axis-aligned + rotated bbox).',
  'Visual embedding — SigLIP-2 / DINOv2 fine-tuned (contrastive on card_identity), 1024-dim.',
  'ANN search in Qdrant — top-K (K=20) candidates, filtered by detected game.',
  'OCR — PaddleOCR for name/number/set; cross-check vs candidates.',
  'Final selection — argmax of joint score (cos-sim × OCR match × popularity prior).',
  'Condition grading — multi-head ResNet/EfficientNet predicting centering, corners, edges, surface, overall.',
  'Compose result — card + 30d comps + condition + grade-ladder ROI.',
];
pipeline.forEach(s => children.push(num(s)));

children.push(h2('5.2 Training data plan'));
children.push(bullet('Catalog images from official APIs to pretrain embeddings via self-supervised contrastive (random crop, blur, glare, perspective).'));
children.push(bullet('Real-world photos seeded from user uploads (consent-gated), public datasets, plus reference photos per major TCG.'));
children.push(bullet('Condition labels from eBay seller-declared PSA grades aligned to listing image, filtered for trustworthiness, augmented with controlled photos of known graded slabs.'));

children.push(h2('5.3 Serving'));
children.push(p('All models served as Modal endpoints; autoscale on GPU; CPU fallback for embeddings; stable JSON contracts in apps/ml/contracts.md.'));

children.push(h2('5.4 Evaluation harness'));
children.push(bullet('Held-out set per game: 500+ photos, hand-labelled.'));
children.push(bullet('Metrics: top-1, top-5, mean confidence, p50/p95 latency, condition MAE vs ground truth.'));
children.push(bullet('CI runs the eval on every model PR and gates merges.'));

// 6 Agentic
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h1('6. Agentic Layer'));
children.push(p('LangGraph orchestrates a set of independently testable subagents. Default LLM is Claude Haiku 4.5; escalate to Claude Sonnet 4.6 only for synthesis (Grade ROI verdict, Daily Digest, anomaly judgement). Every call is wrapped in a token + cost budget guard and LangSmith tracing.'));

children.push(h2('6.1 Subagents'));
children.push(table(
  ['Agent', 'Trigger', 'Output'],
  [
    ['ScanAgent', 'User uploads photo', 'card_match, condition'],
    ['PricingAgent', 'After scan / on card detail load', 'comps_30d, active_listings, chart_series'],
    ['GradeROIAgent', 'After ScanAgent + PricingAgent', 'BUY / SELL / HOLD / GRADE verdict + $ delta'],
    ['MonitorAgent (long-running)', 'User sets alert', 'Push notification / email'],
    ['FlipFinderAgent (stretch)', 'Continuous', 'Ranked underpriced listings'],
    ['AnomalyAgent', 'On sale-event ingest', 'Suspicious sale flag'],
    ['DigestAgent', 'Daily cron per user', 'Personalised briefing'],
  ],
  [2400, 3680, 4000]
));

children.push(h2('6.2 Why LangGraph (not just CrewAI)'));
children.push(p('LangGraph offers stateful, branching workflows with retries, human-in-the-loop hooks, and replayable traces via LangSmith — exactly what we need for production agentic flows that affect real money decisions. CrewAI is great for prototyping; we use it locally for spikes but the production system is LangGraph.'));

// 7 UX
children.push(h1('7. UX / UI Plan (web v1)'));
const pages = [
  ['/', 'Landing — value prop, demo scan video, no-login try-scan CTA.'],
  ['/scan', 'Drag-drop / camera capture, live detection preview, result slide-up.'],
  ['/card/[slug]', 'SSR card detail: hero image, condition badge, price tiles, 90d chart, comps table (filterable by source/grade), grade-ladder ROI panel, add-to-portfolio, set-alert.'],
  ['/search', 'Text + image search, filters by game / set / rarity.'],
  ['/portfolio', 'Total value, daily-change spark, top movers, grade distribution, suggested actions.'],
  ['/alerts', 'List, create, edit alerts.'],
  ['/account', 'Stripe billing portal.'],
  ['/admin', 'Internal data quality + ingest health.'],
];
children.push(table(['Path', 'Purpose'], pages, [1800, 8280]));

children.push(p('Mobile-first responsive. Each /card/[slug] is statically generated + ISR-refreshed for long-tail SEO — Card Ladder gates this content, we don’t.'));

// 8 Roadmap
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h1('8. Roadmap (90 days, solo)'));
children.push(table(
  ['Week', 'Milestone', 'Deliverable'],
  [
    ['1', 'Repo + infra', 'Monorepo bootstrapped, CI green, Postgres + Qdrant + Redis local; Modal + Vercel; AGENTS.md + CLAUDE.md committed'],
    ['2', 'Catalog ingest', 'Pokemon + MTG + YGO catalogs ingested; card_identity populated; image-embedding job end-to-end'],
    ['3', 'Catalog completion', 'Lorcana + One Piece + sports MVP (top 20k); Qdrant index live'],
    ['4', 'eBay ingest', 'Browse active + Insights sold; sale_event populated; daily roll-ups'],
    ['5', 'TCGPlayer + Cardmarket', 'Third-party API or scraper wired in; cross-source normalisation'],
    ['6', 'Scan API v0', 'Detection + embedding ANN; top-K endpoint <2.5s p95'],
    ['7', 'Scan refinement', 'OCR re-rank + game prior; condition grader v0'],
    ['8', 'Search + card detail', 'Public, indexable, fast'],
    ['9', 'Scan flow web', 'Webcam + upload, polished result UI'],
    ['10', 'Auth + portfolio + alerts', 'Clerk + Stripe + Temporal scheduled jobs'],
    ['11', 'Agentic layer', 'LangGraph: ScanAgent → PricingAgent → GradeROIAgent; DigestAgent stretch'],
    ['12', 'Hardening + private beta', 'Eval harness, observability dashboards, 25-user closed beta'],
  ],
  [900, 2880, 6300]
));

// 9 KPIs
children.push(h1('9. KPIs (Phase 1 success criteria)'));
children.push(bullet('Scan accuracy: top-1 ≥ 90% across all supported games on held-out eval; top-5 ≥ 98%.'));
children.push(bullet('Scan latency: p95 < 2.5s end-to-end on web.'));
children.push(bullet('Price freshness: ≥ 95% of top-10k cards have a comp from the last 24h.'));
children.push(bullet('Coverage: every supported game has ≥ 95% of in-print cards indexed.'));
children.push(bullet('Beta NPS ≥ 40 after 4 weeks of closed beta.'));
children.push(bullet('Unit economics: LLM cost per Pro user < $0.30/month at projected usage.'));

// 10 Risks
children.push(h1('10. Risks & Mitigations'));
children.push(table(
  ['Risk', 'Likelihood', 'Mitigation'],
  [
    ['eBay Marketplace Insights rejection', 'Medium', 'Apply Day 1; fall back to Browse + permitted scraping; bridge via Poketrace'],
    ['TCGPlayer API still closed', 'High', 'Use TCG API.dev / TCGAPIs.com; $50–$100/mo budget'],
    ['Cardmarket data quality', 'Medium', 'Apify scrapers; cache aggressively'],
    ['Model accuracy below target', 'Medium', 'Top-K confirm UI + active learning from user confirmations'],
    ['Scraping ToS / legal', 'Medium', 'Prefer official APIs; document compliance in docs/legal'],
    ['Solo founder burnout', 'Always', 'Strict scope; weekly review; agent-assisted coding'],
    ['GPU cost overrun', 'Low/Med', 'Modal pay-per-second; CPU fallback; embedding cache'],
  ],
  [2800, 1600, 5680]
));

// 11 Phase 2/3
children.push(h1('11. Phase 2 & 3 preview'));
children.push(bullet('Phase 2 (months 4–6): Native iOS/Android (React Native), live grading via video stream, sealed product, dealer/POS tier, affiliate revenue.'));
children.push(bullet('Phase 3 (months 7–12): In-app marketplace (escrow, shipping, authentication), live auctions, social/feed, ML price forecasting.'));

// 12 Next session instructions
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h1('12. Instructions for the Next Claude / Cursor Session'));
children.push(p('Use TCG_Scan_Phase1.md as the source of truth. Treat the following Cursor Prompt Seeds as the stepwise scaffolding menu. Each seed is reproduced in full inside the markdown companion (sections 12.1–12.9).'));

children.push(h3('Step 1 — Scaffold the monorepo'));
children.push(bullet('Turborepo + pnpm; apps/(web, api, worker, ml); packages/(sdk-ts, sdk-py, ui, schema, agents); infra docker-compose for postgres-16, qdrant, redis; AGENTS.md + CLAUDE.md; GitHub Actions baseline.'));

children.push(h3('Step 2 — Catalog ingest'));
children.push(bullet('Implement ingesters for Pokemon (pokemontcg.io), MTG (Scryfall), YGO (YGOPRODeck), Lorcana (lorcast); Alembic migrations for card_identity, sale_event, card_price_daily; embedding upsert to Qdrant collection "cards".'));

children.push(h3('Step 3 — Pricing ingest'));
children.push(bullet('Temporal workers: ebay_active, ebay_sold (with Browse-only fallback), tcgplayer, cardmarket; nightly roll-ups into card_price_daily.'));

children.push(h3('Step 4 — Scan API + ML'));
children.push(bullet('Modal endpoints for detect (YOLOv11-nano), embed (DINOv2-base), ocr (PaddleOCR), grade (ResNet50 multi-head, placeholder weights). FastAPI /v1/scan orchestrates the pipeline; Redis caches embeddings.'));

children.push(h3('Step 5 — Web app'));
children.push(bullet('Pages per §7. SDK auto-generated from FastAPI OpenAPI. Mobile-first responsive. ISR for /card/[slug].'));

children.push(h3('Step 6 — Agentic layer'));
children.push(bullet('LangGraph graphs: scan_graph, monitor_graph, digest_graph. Claude Haiku default; Sonnet for synthesis; LangSmith tracing; cost-budget guards.'));

children.push(h3('Step 7 — Eval harness + observability'));
children.push(bullet('apps/ml/eval runner; GitHub Action posts eval report; OpenTelemetry → Grafana Cloud; Sentry on web/api/worker; LangSmith project tcg-scan-prod.'));

children.push(h3('Step 8 — Beta launch checklist'));
children.push(bullet('Cross-check §9 KPIs; run the deploy-checklist skill.'));

// 13 Open Q
children.push(h1('13. Open Questions for RJ'));
children.push(num('Region for v1: US-first (eBay USD), UK/EU (Cardmarket), or global Day 1? Default: US-first with EU price layer.'));
children.push(num('Affiliate revenue from Day 1 (eBay Partner Network, TCGPlayer affiliate)?'));
children.push(num('Brand: TCG Scan final, or alternatives (TCG Lens, CardSight, ScanLadder)?'));
children.push(num('Pricing tiers: Free (10 scans/day, 25 portfolio items), Pro $9.99/mo (unlimited scans, unlimited portfolio, alerts, daily digest), Dealer $39/mo (Phase 2). Acceptable?'));
children.push(num('Grading partnership (PSA / SGC / CGC) in Phase 2?'));

// 14 Sources
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h1('14. Sources'));
const sources = [
  ['130point', 'https://130point.com/'],
  ['130 Point — App Store', 'https://apps.apple.com/us/app/130-point/id6504721152'],
  ['130point overview', 'https://diversinet.com/130point/'],
  ['Card Ladder', 'https://www.cardladder.com/'],
  ['Card Ladder Pricing', 'https://www.cardladder.com/pricing'],
  ['Why Card Ladder', 'https://www.cardladder.com/why-card-ladder'],
  ['Slabfy — Card Ladder alternatives', 'https://slabfy.com/blog/card-ladder-alternative'],
  ['Slabfy — Best sports card apps 2026', 'https://slabfy.com/blog/best-sports-card-apps-2026'],
  ['Eyevo — Pokemon scanner comparison', 'https://eyevotcg.com/blog/best-pokemon-card-scanner-apps-2026/'],
  ['CardPriceIQ — Tested scanner ranking', 'https://cardpriceiq.com/news/best-card-scanner-apps-2026'],
  ['Ludex', 'https://www.ludex.com/'],
  ['Collectr', 'https://getcollectr.com/'],
  ['Market Movers', 'https://www.marketmoversapp.com/'],
  ['CardGrader', 'https://cardgrader.ai/'],
  ['CardGrade.io', 'https://cardgrade.io/'],
  ['TCG AI PRO', 'https://tcgai.pro/'],
  ['eBay Marketplace Insights API', 'https://developer.ebay.com/api-docs/buy/marketplace-insights/static/overview.html'],
  ['TCG API.dev', 'https://tcgapi.dev/'],
  ['TCGAPIs.com', 'https://tcgapis.com/'],
  ['Cardmarket API', 'https://help.cardmarket.com/en/cardmarket-api'],
  ['Poketrace developers', 'https://poketrace.com/developers'],
  ['LangGraph vs CrewAI (Alice Labs)', 'https://alicelabs.ai/en/insights/best-ai-agent-frameworks-2026'],
  ['Multi-agent frameworks in production (47Billion)', 'https://47billion.com/blog/ai-agents-in-production-frameworks-protocols-and-what-actually-works-in-2026/'],
  ['Cursor 2.4 subagents', 'https://www.aimakers.co/blog/cursor-2-4-subagents/'],
  ['AGENTS.md guide', 'https://vibecoding.app/blog/agents-md-guide'],
  ['Vector DB comparison (Medium)', 'https://medium.com/data-science-collective/pinecone-vs-weaviate-vs-qdrant-vs-milvus-66d5bfbcc460'],
];
sources.forEach(([title, url]) => {
  children.push(new Paragraph({
    numbering: { reference: 'bullets', level: 0 },
    children: [link(title, url)],
    spacing: { after: 60 },
  }));
});

// ---------- document ----------
const doc = new Document({
  creator: 'TCG Scan Planning',
  title: 'TCG Scan — Phase 1 Plan v1.0',
  styles: {
    default: { document: { run: { font: 'Calibri', size: 22 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 32, bold: true, font: 'Calibri', color: '0F3D7A' },
        paragraph: { spacing: { before: 360, after: 180 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 26, bold: true, font: 'Calibri', color: '1F4E79' },
        paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 1 } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 22, bold: true, font: 'Calibri', color: '2E75B6' },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: 'bullets',
        levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: 'numbers',
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: PAGE_W, height: PAGE_H },
        margin: { top: MARGIN, right: MARGIN, bottom: MARGIN, left: MARGIN },
      },
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          tabStops: [{ type: TabStopType.RIGHT, position: CONTENT_W }],
          children: [
            new TextRun({ text: 'TCG Scan — Phase 1 Plan', font: 'Calibri', size: 18, color: '595959' }),
            new TextRun({ text: '\tConfidential — Draft v1.0', font: 'Calibri', size: 18, color: '595959' }),
          ],
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [
            new TextRun({ text: 'Page ', font: 'Calibri', size: 18, color: '595959' }),
            new TextRun({ children: [PageNumber.CURRENT], font: 'Calibri', size: 18, color: '595959' }),
            new TextRun({ text: ' of ', font: 'Calibri', size: 18, color: '595959' }),
            new TextRun({ children: [PageNumber.TOTAL_PAGES], font: 'Calibri', size: 18, color: '595959' }),
          ],
        })],
      }),
    },
    children,
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync('TCG_Scan_Phase1.docx', buf);
  console.log('wrote', buf.length, 'bytes');
});
