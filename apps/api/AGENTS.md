# apps/api — AGENTS.md

FastAPI at `/v1`. Thin routes → `services/` → `repositories/`. Async only.

Auth via Clerk middleware. Long jobs return `202` + SSE.
