# apps/api — AGENTS.md

FastAPI at `/v1`. Thin routes → `services/` → `repositories/`. Async only.

Auth via Supabase JWT middleware. Long jobs return `202` + SSE.
