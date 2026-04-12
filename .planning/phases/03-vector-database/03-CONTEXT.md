# Phase 3: Vector Database - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Semantic search over memories, tasks, artifacts, and messages via Turso/libSQL native vector columns (F32_BLOB + DiskANN). Shipped as opt-in beta feature. When Turso is configured, vector search is available; on local SQLite, vector endpoints return 503 with a clear message. Auto-indexing generates embeddings on write via background tasks. No changes to existing non-vector functionality.

</domain>

<decisions>
## Implementation Decisions

### Embedding Strategy
- **D-01:** Configurable embedding backend - default to local sentence-transformers ('all-MiniLM-L6-v2', 384 dims), allow OpenAI text-embedding-3-small (1536 dims) via env var `AGENTHUB_EMBEDDING_PROVIDER=openai`
- **D-02:** Local sentence-transformers runs offline, no API costs - primary path for OSS users
- **D-03:** OpenAI path requires `AGENTHUB_OPENAI_API_KEY` env var, gracefully degrades to disabled if missing
- **D-04:** Embedding generation is async via FastAPI BackgroundTasks - writes return immediately (~10ms), embeddings appear in index within 1-2 seconds
- **D-05:** Model dimension must match schema - switching providers requires schema migration or separate columns per model

### Storage + Indexing
- **D-06:** Turso/libSQL F32_BLOB columns are the primary target for vector storage - this is "Turso preferred and always" per user
- **D-07:** DiskANN indexing from day one via `libsql_vector_idx()` - satisfies VEC-03 and scales to millions of rows
- **D-08:** Local SQLite fallback: app starts normally, vector endpoints return 503 "vector search requires Turso configuration" when Turso not configured
- **D-09:** Startup warning logged when running on local SQLite without Turso credentials (reminds developers vector features are disabled)
- **D-10:** zvec library is REPLACED by native Turso vectors per VEC-01 - zvec dependency should be removed or marked as legacy
- **D-11:** Vector columns stored on the existing shared_memory, tasks, artifacts, messages tables via Alembic migration (not separate vector table)

### Auto-indexing Hooks
- **D-12:** All 4 content-bearing entities get auto-indexed: memories (shared_memory.value), tasks (description + output), artifacts (content), messages (content)
- **D-13:** Embedding failure handling: log error, entity saves successfully without embedding, background retry every 5 minutes until success
- **D-14:** Failed embeddings are marked with `embedding_status = 'failed'` (or NULL for pending) so health checks can surface unindexed records
- **D-15:** Re-indexing endpoint (admin-only) to regenerate embeddings after model change or bulk backfill

### Search API Design
- **D-16:** Hybrid API: unified `POST /v1/search` for cross-entity queries + per-entity convenience shortcuts (`POST /v1/memory/search`, `POST /v1/tasks/search`, etc.)
- **D-17:** Per-entity shortcuts internally call the unified endpoint - single implementation
- **D-18:** Default `top_k=10`, maximum `top_k=50` - validated at API layer, returns 400 Problem Details on violation
- **D-19:** Unified search accepts `{query, types: ['memory','task','artifact','message'], filters, top_k}` - types defaults to all
- **D-20:** Results ranked by cosine similarity (vector_distance_cos), cross-entity results merged by score
- **D-21:** Filters support owner_agent_id, created_after, created_before, tags/labels at minimum

### Opt-in Beta Framing (VEC-06)
- **D-22:** Feature flag `AGENTHUB_VECTOR_SEARCH_ENABLED` defaults to `true` when Turso configured, `false` otherwise
- **D-23:** Endpoints documented as `[experimental]` in OpenAPI - visible at /docs with beta badge
- **D-24:** CHANGELOG and README note beta status
- **D-25:** Beta status does not mean hidden - endpoints are visible and testable, just flagged

### Claude's Discretion
- Exact sentence-transformers loading pattern (lazy vs eager at startup)
- Background task queue implementation (FastAPI BackgroundTasks vs separate worker)
- DiskANN index build parameters (M, efConstruction)
- Test strategy for Turso-only features (mocking vs skipping locally)
- Re-indexing endpoint request/response shape
- Index maintenance (rebuild on model change, vacuum cadence)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Database Layer (Turso Foundation)
- `app/database/connection.py` - Turso URL/token detection, libSQL import fallback, parameter adapter
- `app/database/models.py` - 16 SQLAlchemy models (add vector columns here)
- `alembic/versions/0001_initial_schema.py` - Initial migration pattern to follow
- `.planning/phases/01-backend-hardening/01-04-SUMMARY.md` - Alembic setup details

### Configuration
- `app/config.py` - Settings class with `AGENTHUB_` prefix; `zvec_path`, `embedding_model`, `vector_batch_size` already defined

### Target Entities (Content Fields to Embed)
- `app/database/models.py` - SharedMemoryModel.value, TaskModel.description/output, ArtifactModel.content, MessageModel.content
- `app/api/routes_memory.py` - Current LIKE-based search_memory() to upgrade
- `app/api/routes_tasks.py` - Task lifecycle routes (Phase 2 added broadcast hooks here)
- `app/api/routes_artifacts.py` - Artifact endpoints
- `app/api/routes_messaging.py` - Message endpoints

### Patterns from Prior Phases
- `app/middleware.py` - RFC 7807 error format (Phase 1) - apply to vector endpoints
- `app/services/connection_manager.py` - Background async task pattern (Phase 2) - model for embedding workers
- `app/main.py` - lifespan startup with service initialization (Phase 2)

### External Documentation
- Turso Vector Docs: https://docs.turso.tech/features/ai-and-embeddings
- libSQL F32_BLOB: vector_distance_cos, libsql_vector_idx, vector_top_k
- sentence-transformers: https://www.sbert.net/docs/pretrained_models.html

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/database/connection.py` already detects Turso via TURSO_DATABASE_URL + TURSO_AUTH_TOKEN env vars
- `app/config.py` has `embedding_model="sentence-transformers/all-MiniLM-L6-v2"` pre-configured
- `app/api/routes_memory.py` has LIKE-based search to replace with vector search
- `app/services/connection_manager.py` (Phase 2) provides pattern for async background tasks
- `app/middleware.py` RFC 7807 error format applies to new endpoints

### Established Patterns
- FastAPI Depends() for DI
- Service layer pattern (routes -> services -> repositories)
- Alembic migrations with CREATE TABLE IF NOT EXISTS for backward compat
- structlog with trace_id binding
- Env var config via pydantic-settings

### Integration Points
- Alembic migration adds `embedding BLOB`, `embedding_model TEXT`, `embedding_status TEXT` columns to shared_memory/tasks/artifacts/messages
- New `app/services/embedding_service.py` wraps sentence-transformers and OpenAI
- New `app/services/vector_search_service.py` wraps Turso vector queries
- Route handlers in memory/tasks/artifacts/messages add BackgroundTasks dependency for async embedding
- New `app/api/routes_search.py` for unified /v1/search endpoint
- Per-entity search routes get new /search subpath that delegates to unified service

</code_context>

<specifics>
## Specific Ideas

- The requirements explicitly say "replacing zvec" - zvec dependency should be removed from requirements.txt in the cleanup task
- Turso is mandatory for vector features - this is a deliberate design decision, not a limitation. Local SQLite users get a clear 503 explaining why
- DiskANN is required by VEC-03 - this means the migration must use `libsql_vector_idx(embedding, 'diskann')` for index creation
- Background embedding tasks should log trace_id matching the write request that spawned them (for debuggability)

</specifics>

<deferred>
## Deferred Ideas

- Real-time embedding updates over WebSocket (would need WS-07 in a future phase)
- Multi-language embedding model support (only English for v1)
- Re-ranking with cross-encoders after vector retrieval (quality improvement for future)
- Hybrid search (BM25 + vector) - v1 is vector-only
- Vector compression/quantization (int8, binary) for storage savings

</deferred>

---

*Phase: 03-vector-database*
*Context gathered: 2026-04-12*
