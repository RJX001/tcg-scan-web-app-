# apps/api — AGENTS.md

FastAPI at `/v1`. Thin routes → `services/` → `repositories/`. Async only.

Auth via Supabase JWT middleware (`request.state.user`); protected handlers call `resolve_db_user`. Long marketplace ingest belongs in `apps/worker` / CLI — keep HTTP handlers short.
