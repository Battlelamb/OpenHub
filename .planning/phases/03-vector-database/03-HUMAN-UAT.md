---
status: resolved
phase: 03-vector-database
source: [03-VERIFICATION.md]
started: 2026-04-13T00:00:00Z
updated: 2026-04-13T09:05:00Z
---

## Current Test

[all 3 items validated against live Turso on hub.brunhilde.cloud]

## Tests

### 1. Turso vector binding smoke test
expected: `scripts/smoke_turso_vector.py` run against a real Turso DB exits 0 and confirms `vector32(json.dumps(vec))` binding works end-to-end (insert + retrieve vector).
result: pass
evidence: 8/9 turso-gated pytest tests pass against live Turso EU (1 xfail canary is the historical stricter-binding check, documented in commit 1e0e1f1). `test_binding_roundtrip` directly exercises the `vector32(json.dumps(vec))` path and confirms cosine distance ~0 on roundtrip. All 52 non-smoke-script integration tests (turso + auto-indexing + search-api) also pass on VPS venv.

### 2. End-to-end semantic search (SC-1)
expected: With a live Turso DB + embeddings enabled, `POST /v1/search` with a natural-language query returns at least one hit ordered by cosine distance.
result: pass
evidence: `curl -X POST https://hub.brunhilde.cloud/v1/search -d '{"query":"kredi basvuru takibi","top_k":5}'` returns 5 hits, distance-ordered ascending (0.72 -> 0.82), mix of `task` and `message` entity types. Turkish query yielded Turkish content correctly via the `paraphrase-multilingual` (mpnet-base-v2, 768-dim) Ollama model. `test_end_to_end_search` integration test also passes against live Turso.

### 3. Persistence across restart (SC-2)
expected: After writing memory/task/artifact/message rows with embeddings and running a service restart, F32_BLOB columns survive and `/v1/search` still returns the same hits.
result: pass
evidence: After `screen -S openhub -X quit && screen -dmS openhub ...` restart of the uvicorn process on VPS, the same query (`kredi basvuru takibi`, top_k=5) returned identical hits with identical cosine distances down to the last decimal. Embedding data is durably persisted in Turso (libsql://openhub-eu-battlelamb.aws-eu-west-1.turso.io) F32_BLOB(768) columns across the 4 target tables (shared_memory, tasks, artifacts, messages).

## Summary

total: 3
passed: 3
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

None. Phase 3 vector search is live in production with multilingual support.

## Notes for follow-up phases

- Retry worker is actively backfilling existing rows (observed ~1 embedding/second for pre-existing memory/task/message rows on VPS). Full backfill will complete naturally via the 5-minute retry tick.
- Alembic/Turso disconnect discovered during deploy: `alembic upgrade head` in `app/main.py` lifespan runs against local SQLite, not Turso. Schema was applied to Turso manually via `/tmp/apply_vector_migration_turso.py` using libsql remote-only mode. Follow-up: wire alembic to run against Turso when `AGENTHUB_TURSO_DATABASE_URL` is set, or document the manual-apply step in the deploy runbook.
- `docker-compose.yml` still carries dead `AGENTHUB_ZVEC_PATH` / `./data/zvec` lines (lines 12, 19). VPS uses systemd/screen, not compose, so this is cosmetic. Clean up in a follow-up commit.
