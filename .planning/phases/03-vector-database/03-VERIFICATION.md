---
phase: 03-vector-database
verified: 2026-04-13T10:30:00Z
status: passed
score: 4/4 Success Criteria verified + all 3 HUMAN-UAT items closed against live Turso on 2026-04-13
re_verification: null
closed_at: 2026-04-13T09:10:00Z
closed_by: phase 3 deploy to hub.brunhilde.cloud with paraphrase-multilingual (768-dim) via Ollama; see 03-HUMAN-UAT.md for evidence
human_verification:
  - test: "Turso vector binding smoke test"
    expected: "scripts/smoke_turso_vector.py writes a 384-dim vector via vector32(json.dumps(vec)) and reads it back with vector_distance_cos < 0.01 against a real Turso DB"
    why_human: "Requires live Turso credentials (TURSO_DATABASE_URL + TURSO_AUTH_TOKEN); research flagged the vector32 JSON-string binding pattern as MEDIUM confidence - the entire phase builds on it. Research and code are consistent with the documented pattern, but only a live round-trip can confirm libsql-python accepts it at runtime."
  - test: "End-to-end semantic search against live Turso"
    expected: "POST /v1/search with types=['memory'] returns hits ordered by cosine distance ascending after writing known fixtures into shared_memory via the regular write path"
    why_human: "Success Criterion 1 (vector similarity returns semantically relevant results using vector_distance_cos) is provable only against a real Turso DB. All 4 shortcut routes + unified endpoint are wired and code-correct, but the SQL only executes on Turso."
  - test: "Persistence across restart (Success Criterion 2)"
    expected: "A row embedded via auto-index then matched via /v1/search remains findable after `docker compose restart agenthub`, confirming F32_BLOB columns survive restart"
    why_human: "Cannot be verified statically - needs live Turso + process restart. Code path is in place (columns are persistent ALTER TABLE ADD, embeddings flushed via UPDATE on write path)."
gaps: []
---

# Phase 03: Vector Database Verification Report

**Phase Goal:** Semantic search over memories, tasks, and artifacts is available via a REST API backed by Turso/libSQL native vector columns, shipped as an opt-in beta feature.

**Verified:** 2026-04-13T10:30:00Z
**Status:** human_needed
**Re-verification:** No - initial verification
**Score:** 4/4 Success Criteria code-verified (1 gated on live-Turso spot-check)

## Goal Achievement

### Success Criteria (from ROADMAP.md)

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 1 | Vector similarity search over stored memories returns semantically relevant results using vector_distance_cos | ? HUMAN | `app/services/vector_search_service.py` `search_entity` issues `vector_top_k + vector_distance_cos` SELECT with rowid join (lines 178-186); unified route at `POST /v1/search` wired via `routes_search.unified_search`. Live Turso DB required to execute SQL. |
| 2 | Vectors survive a server restart - F32_BLOB persistence | ? HUMAN | Migration `alembic/versions/0003_vector_columns.py` adds persistent `embedding F32_BLOB(384)` columns to 4 tables via `ALTER TABLE ADD COLUMN`; `write_embedding` issues UPDATE which commits to DB. Persistence is code-true; needs live round-trip to confirm. |
| 3 | New memory, task, artifact, and message writes automatically generate and store embeddings | VERIFIED | `schedule_embedding` imported and called in all 4 write routes: `routes_memory.py:65,79`, `routes_tasks.py:101`, `routes_artifacts.py:71`, `routes_messaging.py:118`. `embedding_hooks._embed_and_store` never-raises, calls `backend.embed` then `svc.write_embedding`, handles failure via `mark_failed`. |
| 4 | Feature documented as experimental/opt-in - server starts and operates normally with vector search disabled | VERIFIED | `is_vector_enabled()` returns False on local SQLite (confirmed at runtime: import chain succeeds + `is_vector_enabled()=False` without errors). Startup lifespan logs `vector_search_disabled` warning. Retry worker is a no-op. `require_vector` dependency returns RFC 7807 503. README, CHANGELOG, .env.example all document beta status. OpenAPI tag `search [experimental]` registered in `app/main.py` openapi_tags. |

**Code-verified score:** 4/4. Criteria 1 and 2 additionally require a live-Turso spot-check (documented as deployment gate, tracked in 03-02 and 03-05 SUMMARYs).

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `alembic/versions/0003_vector_columns.py` | F32_BLOB(384) migration + DiskANN index | VERIFIED | 93 lines, `F32_BLOB(384)` + `libsql_vector_idx(embedding, 'metric=cosine')` on 4 tables; `_safe_execute` tolerates local-SQLite errors; idempotent ADD COLUMN |
| `app/database/vector_availability.py` | is_vector_enabled() + require_vector() | VERIFIED | 52 lines, honours `Settings.vector_search_enabled` (False override wins), auto-detect via `Database._use_turso`, RFC 7807 503 payload |
| `app/services/vector_search_service.py` | VectorSearchService + ENTITY_CONFIG | VERIFIED | 284 lines; `write_embedding` uses `vector32(:vec)` + `json.dumps(vector)`; `search_entity` uses `vector_top_k` with `t.rowid = v.id` (per RESEARCH Pitfall 5); filters applied in OUTER WHERE (Pitfall 3); `mark_failed`, `mark_pending`, `list_unindexed` (with optional `since` filter for D-15), `clear_embedding` (sets NULL + status='deleted', does not DELETE row) |
| `app/services/embedding_service.py` | LocalSentenceTransformerBackend + OpenAIBackend + factory | VERIFIED | 183 lines; `@runtime_checkable Protocol`; local backend lazy-loads `sentence_transformers` inside `_ensure_model()` (confirmed at runtime: `sentence_transformers` and `torch` absent from `sys.modules` after import); OpenAI backend lazy-imports `AsyncOpenAI`; factory returns `None` when provider=openai and key missing |
| `app/services/embedding_hooks.py` | schedule_embedding + _embed_and_store | VERIFIED | 119 lines; short-circuits on `is_vector_enabled() is False`, unknown entity type, empty text; `_embed_and_store` never-raises (every failure path wrapped, calls `mark_failed` defensively); propagates structlog `trace_id` via contextvars |
| `app/services/embedding_retry_worker.py` | start/stop lifespan tasks, _run_once | VERIFIED | 146 lines; `RETRY_INTERVAL_SECONDS=300` (D-13 5 min); iterates all 4 `ENTITY_CONFIG` keys; `start_retry_worker` no-ops when `is_vector_enabled() is False`; asyncio-Task-managed with cancellation |
| `app/api/routes_search.py` | POST /v1/search + /reindex + DELETE /{entity_type}/{id} | VERIFIED | 273 lines; router prefix `/v1/search`, tag `search [experimental]`, router-level `Depends(require_vector)`; `unified_search` helper (reused by shortcut routes); `reindex_embeddings` admin-only via `CurrentAdmin`, accepts `entity_type` + `since`, falls back gracefully when list_unindexed lacks `since`; `delete_embedding` admin-only, RFC 7807 400/404/503 paths |
| `app/models/vector_search.py` | SearchRequest, SearchHit, SearchResponse + reindex/delete models | VERIFIED | 89 lines; `ENTITY_TYPES=['memory','task','artifact','message']`; `SearchRequest` has `top_k: int = Field(default=10, ge=1, le=50)` (rejects 0 and 51 at Pydantic layer); `ReindexRequest`, `ReindexResponse`, `DeleteEmbeddingResponse` |
| `app/main.py` | Retry worker lifespan + openapi_tags + startup warning + search router include | VERIFIED | `start_retry_worker`/`stop_retry_worker` awaited in lifespan (lines 77-85, 110-114); `vector_search_disabled` warning with hint when disabled (lines 90-100); `openapi_tags` with `"search [experimental]"` description (lines 129-140); `include_router(search_router)` (line 249) |
| `scripts/smoke_turso_vector.py` | Standalone Turso binding smoke test | VERIFIED | 90 lines; reads both `TURSO_*` and `AGENTHUB_TURSO_*` env var forms, exit code 2 on SKIP, asserts roundtrip via `VectorSearchService` |
| `README.md` | Vector Search (Beta) section | VERIFIED | Section at line 141 with `AGENTHUB_EMBEDDING_PROVIDER`, `AGENTHUB_OPENAI_API_KEY`, `AGENTHUB_VECTOR_SEARCH_ENABLED`, and explicit-disable note at line 211 |
| `CHANGELOG.md` | Phase 3 entry with VEC-01..VEC-06 | VERIFIED | `## [Phase 3 - Vector Database]` heading (line 5); VEC-01 and VEC-06 mentioned explicitly; "search [experimental]" OpenAPI tag noted |
| `.env.example` | Documented vector env vars | VERIFIED | `# Vector Search (Phase 3 Beta)` section (line 27) with all 3 env vars commented |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `alembic/versions/0003_vector_columns.py` | shared_memory, tasks, artifacts, messages | `ALTER TABLE ADD COLUMN embedding F32_BLOB(384)` | WIRED | 4 tables x 5 columns (embedding, embedding_model, embedding_status, embedding_error, embedded_at) |
| `vector_availability.is_vector_enabled` | `Settings.vector_search_enabled` + `Database._use_turso` | runtime predicate | WIRED | Runtime check returns False on local SQLite; False override wins; auto-mode ties to Turso |
| `requirements.txt` | package installs | removal of zvec line | WIRED | `^zvec` grep returns no matches |
| `VectorSearchService` | `Database.execute / fetch_all` | constructor `self.db` | WIRED | `def __init__(self, db: Database): self.db = db` |
| `VectorSearchService` | Turso `vector32 / vector_top_k / vector_distance_cos` | parameterized SQL + `json.dumps` | WIRED | `vector32(:vec)` with `json.dumps(vector)` binding in both write and search paths (per RESEARCH Pattern 2) |
| `get_embedding_service()` | `Settings.embedding_provider + openai_api_key` | `get_settings()` lookup | WIRED | Returns None gracefully when provider=openai without key |
| `LocalSentenceTransformerBackend.embed` | `sentence_transformers.SentenceTransformer` | lazy import inside `_ensure_model()` | WIRED | Confirmed at runtime: `sentence_transformers not in sys.modules` after import chain |
| `routes_memory.py write_memory` | `schedule_embedding` | `BackgroundTasks.add_task` | WIRED | Lines 65 (create path) + 79 (upsert path) |
| `routes_tasks.py create_task` | `schedule_embedding` | `BackgroundTasks.add_task` | WIRED | Line 101 - embeds task.description |
| `routes_artifacts.py upload_artifact` | `schedule_embedding` | `BackgroundTasks.add_task` | WIRED | Line 71 - embeds artifact content |
| `routes_messaging.py send_message` | `schedule_embedding` | `BackgroundTasks.add_task` | WIRED | Line 118 - embeds msg.content |
| `main.py lifespan` | `start_retry_worker` | `await start_retry_worker()` + `stop_retry_worker()` | WIRED | Try/except with defensive logging |
| All 4 auto-index hooks | `is_vector_enabled` | short-circuit before scheduling | WIRED | `schedule_embedding` checks `is_vector_enabled()` first (embedding_hooks.py:99) |
| `routes_search.py` | `require_vector` | `dependencies=[Depends(require_vector)]` router-level | WIRED | Router-level, applies to all 3 endpoints |
| `routes_search.py` | `get_embedding_service + VectorSearchService` | instantiation inside handler | WIRED | Fresh instance per request |
| per-entity /search shortcut routes | `unified_search` | direct call with `types=[single]` | WIRED | routes_memory:201, routes_tasks:619, routes_artifacts:153, routes_messaging:388 (local imports avoid cycle) |
| reindex + delete | `get_current_admin` | `CurrentAdmin` type alias | WIRED | Admin guard present on both routes |
| reindex | `list_unindexed + embed + write_embedding` | service orchestration | WIRED | Batches embed calls, falls back gracefully if list_unindexed lacks `since` arg |
| `main.py lifespan startup` | `is_vector_enabled` | conditional warning log `vector_search_disabled` | WIRED | Lines 90-100 |

### Data-Flow Trace (Level 4)

Phase 03 ships data-flowing components. Dynamic data flows:

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `routes_search.unified_search` | `all_hits` | `VectorSearchService.search_entity` -> Turso SQL `vector_top_k + vector_distance_cos` | Live Turso only | FLOWING (code) / STATIC on local SQLite by design |
| `embedding_hooks._embed_and_store` | `vectors[0]` | `backend.embed([truncated])` -> sentence-transformers or OpenAI API | Yes (real model inference) | FLOWING |
| `embedding_retry_worker._run_once` | `rows` | `VectorSearchService.list_unindexed(entity_type, limit=50)` -> `SELECT` on 4 tables | Yes (reads real DB rows) | FLOWING |
| Auto-index hooks in 4 write routes | `text` | Request body field (memory.value, task.description, artifact.content, msg.content) | Yes | FLOWING |
| `reindex_embeddings` | `rows` / `vectors` | list_unindexed -> backend.embed -> write_embedding | Yes | FLOWING |

Note: `unified_search` returns empty on local SQLite via the `require_vector` 503 short-circuit - this is the documented opt-in beta behaviour, not a stub. On Turso, SQL flows real vectors through vector_top_k.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Core modules import without errors | `python3 -c "from app.api.routes_search import router; ..."` | All imports succeed | PASS |
| sentence-transformers is lazy (not loaded at import) | `'sentence_transformers' in sys.modules` after import chain | False | PASS |
| torch is lazy | `'torch' in sys.modules` after import chain | False | PASS |
| `is_vector_enabled()` returns False on local SQLite | Runtime invocation | False | PASS |
| `ENTITY_CONFIG` has all 4 entity types | Inspect keys | `['artifact','memory','message','task']` | PASS |
| `router.prefix` is `/v1/search` with experimental tag | Inspect router | `/v1/search`, `['search [experimental]']` | PASS |
| Sync vector unit tests | `pytest tests/unit/test_vector_feature_flag.py tests/unit/test_vector_deps.py` | 11/11 passing (env lacks pytest-asyncio and alembic, so async and migration tests could not run locally - orchestrator's canonical suite reports 135 passed, 1 skipped) | PASS |
| zvec removed from requirements.txt | grep `^zvec` | no matches | PASS |
| Startup warning wired | grep `vector_search_disabled` in main.py | Line 93 | PASS |

Note on test environment: The local shell is missing `pytest-asyncio` and `alembic` runtime packages (both declared in requirements.txt). Async-marked tests and the migration test fail only on that dependency boundary - they are not code defects. The orchestrator's authoritative run reports 135 passed, 1 skipped (pre-existing bcrypt), 9 turso-deselected.

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
| ----------- | -------------- | ----------- | ------ | -------- |
| VEC-01 | 03-01, 03-02 | Turso/libSQL native vector columns (F32_BLOB) replacing zvec | SATISFIED | Migration 0003 adds `F32_BLOB(384)` to 4 tables; `zvec` removed from requirements.txt and Settings; `Database._use_turso` drives enablement |
| VEC-02 | 03-02, 03-05 | Vector similarity search using vector_distance_cos | SATISFIED (code) / HUMAN (live) | `search_entity` uses `vector_distance_cos(t.embedding, vector32(:qvec))` in SELECT; `/v1/search` wired. Live Turso round-trip required to observe non-empty ordered hits. |
| VEC-03 | 03-01 | DiskANN vector indexing for ANN search | SATISFIED | Migration creates `idx_{table}_embedding ON {table}(libsql_vector_idx(embedding, 'metric=cosine'))` on all 4 tables; local SQLite tolerates via `_safe_execute` ignore patterns |
| VEC-04 | 03-03, 03-04 | Auto-indexing hooks on memory/task/artifact write paths | SATISFIED | `schedule_embedding` wired into routes_memory (2 call sites), routes_tasks, routes_artifacts, routes_messaging (note: messaging is a bonus fourth type beyond the REQ text); retry worker at 5 min interval |
| VEC-05 | 03-02, 03-05 | Vector search API endpoints (search, index, delete) | SATISFIED | `POST /v1/search` (unified + 4 shortcuts), `POST /v1/search/reindex` (admin, entity_type+since scope), `DELETE /v1/search/{entity_type}/{id}` (admin, clears embedding but not entity); all Pydantic validated and RBAC gated |
| VEC-06 | 03-01, 03-06 | Feature flagged as opt-in beta | SATISFIED | `AGENTHUB_VECTOR_SEARCH_ENABLED` explicit-disable wins; startup WARNING log on local SQLite; OpenAPI `search [experimental]` tag description advertises beta; README Vector Search (Beta) section; CHANGELOG entry; .env.example documents env vars |

All 6 VEC-XX IDs claimed by REQUIREMENTS.md Phase-3 mapping table are accounted for by at least one plan's `requirements:` field. No orphaned requirements.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| (none) | - | - | - | No blocker or warning anti-patterns detected in the 12 key files scanned. No `TODO`, `FIXME`, `placeholder`, `not yet implemented`, or stub `return null/[]/{}` in functional code paths. Empty-return patterns in `VectorSearchService.list_unindexed` / `search_entity` are legitimate "no rows" fallbacks, not stubs - they sit behind real SQL execution. |

### Human Verification Required

Three items need a live Turso DB to close:

#### 1. Turso vector binding smoke test

**Test:** Set `TURSO_DATABASE_URL` + `TURSO_AUTH_TOKEN`, then run `.venv/bin/python scripts/smoke_turso_vector.py`.
**Expected:** Exit code 0 with "OK: roundtrip distance < 0.01" (write a known 384-dim vector via `vector32(json.dumps(vec))`, read back via `vector_distance_cos`).
**Why human:** Requires live Turso credentials. RESEARCH.md flagged the `vector32(JSON-string)` binding pattern as MEDIUM confidence; the entire phase builds on it. Research and code are consistent with the documented pattern, but only a live round-trip can confirm libsql-python accepts it at runtime. Documented as a deployment gate in 03-02-SUMMARY and 03-05-SUMMARY.

#### 2. End-to-end semantic search against live Turso (Success Criterion 1)

**Test:** Against a Turso-backed instance, POST /v1/memory with a few known texts, wait ~5s, then `POST /v1/search` with `{"query": "...", "types": ["memory"], "top_k": 5}`.
**Expected:** 200 response with hits ordered by cosine distance ascending; auto-indexed embeddings visible via embedding_status='ok'.
**Why human:** Only provable against a real Turso DB. All 4 shortcut routes + unified endpoint are wired and code-correct, but the SQL (`vector_top_k`, `vector_distance_cos`) executes only on Turso.

#### 3. Persistence across restart (Success Criterion 2)

**Test:** With Turso configured, write a memory, confirm /v1/search returns it, then `docker compose restart agenthub`, then run /v1/search again.
**Expected:** The same hit is returned post-restart, confirming F32_BLOB columns survive process restart.
**Why human:** Cannot be verified statically - needs live Turso + process restart. Code path is in place (columns are persistent `ALTER TABLE ADD`, embeddings flushed via `UPDATE` on write path).

### Gaps Summary

**No code gaps.** Every must-have truth across all 6 plans has corresponding artifacts that exist, are substantive, are wired, and flow real data. Every VEC-XX requirement is satisfied in code. All 4 write routes auto-index. All 4 per-entity shortcut routes delegate to `unified_search`. The retry worker, startup warning, OpenAPI tag, README, CHANGELOG, and .env.example are all in place.

The phase is **code-complete**. The remaining verification work is operational: execute the three live-Turso checks above before promoting the beta. These are deployment-gate items, not phase-completeness items, and are documented as such in 03-02-SUMMARY.md and 03-05-SUMMARY.md.

---

_Verified: 2026-04-13T10:30:00Z_
_Verifier: Claude (gsd-verifier)_
