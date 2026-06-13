# Beta launch checklist

Cross-check against Phase 1 §9 KPIs before opening the 25-user closed beta.

## Product

- [ ] Scan flow works on mobile Safari + Chrome (upload + camera)
- [x] Card detail shows 90d chart + multi-source comps + active listings
- [x] Search returns catalog matches
- [x] Portfolio add/remove works with auth
- [x] Portfolio summary + estimated value
- [x] Price alerts CRUD (Pro-gated) + MonitorAgent Temporal schedule scaffold
- [x] Stripe checkout + webhook routes (requires keys)
- [x] Free tier limits: 10 scans/day, 25 portfolio items

## ML

- [ ] Modal detect/embed/OCR/grade deployed (or documented stub waiver)
- [ ] Qdrant index populated for target games
- [ ] Eval harness: top-1 ≥ 90%, top-5 ≥ 98% on held-out set
- [ ] Condition MAE ≤ 0.3 grades vs ground truth

## Data

- [ ] eBay sold + active ingest running on schedule
- [ ] TCGPlayer + Cardmarket wired (or documented gaps)
- [ ] ≥ 95% of top-10k cards have comp within 24h

## Ops

- [ ] Sentry on web, api, worker, ml
- [ ] OpenTelemetry → Grafana Cloud
- [ ] LangSmith project for agent traces
- [ ] Stripe Pro tier + free scan limits enforced
- [x] Code: tier gates + Stripe scaffold shipped (configure keys for prod)

## Beta

- [ ] 25 invitees onboarded
- [ ] Feedback channel (Discord/email)
- [ ] NPS survey after 4 weeks (target ≥ 40)
