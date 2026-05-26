# API endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/v1/health` | public | Liveness probe |
| POST | `/v1/scan` | public | Multipart image upload → top-K matches + condition |
| GET | `/v1/cards/slug/{slug}` | public | Card detail by SEO slug |
| GET | `/v1/cards/{id}` | public | Card detail (Redis-cached, TTL 900s) |
| GET | `/v1/cards/{id}/comps` | public | Last-N-days sale comps for a card |
| GET | `/v1/cards/{id}/comps/summary` | public | 30d mean/median/min/max comp stats |
