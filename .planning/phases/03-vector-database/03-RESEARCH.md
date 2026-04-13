# Phase 3: Vector Database - Research

**Researched:** 2026-04-12
**Domain:** Turso/libSQL native vector search, embedding generation, FastAPI async background tasks
**Confidence:** MEDIUM-HIGH (Turso syntax HIGH, Python binding details MEDIUM - driver docs are thin)

## Summary

Phase 3 upgrades OpenHub from LIKE-based text search to semantic vector search backed by Turso's native `F32_BLOB` columns with DiskANN indexing. The existing `Database` wrapper in `app/database/connection.py` already detects Turso, so new work focuses on: (1) an Alembic migration adding `embedding F32_BLOB(dim)` + metadata columns to 4 entity tables, (2) a pluggable `EmbeddingService` with sentence-transformers (default) and OpenAI backends, (3) a `VectorSearchService` issuing `vector_top_k` / `vector_distance_cos` queries, (4) FastAPI BackgroundTasks hooks on write paths, and (5) graceful 503 degradation when Turso is not configured.

The critical unknown going in was "how do you actually pass a float vector as a bound parameter to libSQL from Python?" After cross-referencing Turso docs, the libsql issue tracker, and Turso's own OpenAI blog post, the answer is: **wrap the parameter with the SQL-side `vector32()` function and pass a JSON-array string**, e.g. `INSERT ... VALUES (vector32(?))` with `json.dumps(embedding_list)` as the bound arg. Passing raw bytes via `struct.pack` is a pattern from `sqlite-vec` (a different extension) and is not the documented Turso path. Plans should lock in the JSON-string approach and validate it early with a smoke test.

**Primary recommendation:** Build the embedding pipeline around two orthogonal services (`EmbeddingService` and `VectorSearchService`), use `vector32(?)` with JSON-string binding for all writes, lazy-load sentence-transformers on first use (not at lifespan startup) to keep cold-start fast, and ship the migration with `CREATE INDEX IF NOT EXISTS ... libsql_vector_idx(embedding, 'metric=cosine')` guarded behind a runtime Turso check since local SQLite cannot execute that DDL.

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Embedding Strategy**
- D-01: Configurable embedding backend - default local `sentence-transformers/all-MiniLM-L6-v2` (384 dim), OpenAI `text-embedding-3-small` (1536 dim) via `AGENTHUB_EMBEDDING_PROVIDER=openai`
- D-02: Local sentence-transformers is the offline/no-cost primary path for OSS users
- D-03: OpenAI path requires `AGENTHUB_OPENAI_API_KEY`, gracefully degrades to disabled if missing
- D-04: Embedding generation async via FastAPI BackgroundTasks - writes return immediately (~10ms), embeddings appear 1-2s later
- D-05: Model dimension must match schema - provider switch = migration or parallel columns

**Storage + Indexing**
- D-06: Turso/libSQL F32_BLOB columns are the primary target ("Turso preferred and always")
- D-07: DiskANN indexing from day one via `libsql_vector_idx()` - satisfies VEC-03
- D-08: Local SQLite fallback: app starts; vector endpoints return 503 "vector search requires Turso configuration"
- D-09: Startup warning logged when running on local SQLite without Turso credentials
- D-10: zvec library is REPLACED by native Turso vectors - remove dependency
- D-11: Vector columns live on existing tables (`shared_memory`, `tasks`, `artifacts`, `messages`) via Alembic migration - NOT a separate vector table

**Auto-indexing**
- D-12: All 4 content-bearing entities get auto-indexed (memory value, task description+output, artifact content, message content)
- D-13: Embedding failure: log error, save entity without embedding, background retry every 5 minutes
- D-14: `embedding_status` column: 'pending' | 'ok' | 'failed' (NULL = not yet attempted)
- D-15: Re-indexing endpoint (admin-only) for model change / bulk backfill

**Search API**
- D-16: Hybrid API - unified `POST /v1/search` + per-entity shortcuts
- D-17: Per-entity shortcuts internally delegate to unified endpoint
- D-18: Default `top_k=10`, max `top_k=50`, 400 Problem Details on violation
- D-19: Unified payload `{query, types: ['memory','task','artifact','message'], filters, top_k}`, types defaults to all
- D-20: Results ranked by `vector_distance_cos`, cross-entity merged by score
- D-21: Filters support `owner_agent_id`, `created_after`, `created_before`, `tags/labels`

**Beta Framing (VEC-06)**
- D-22: `AGENTHUB_VECTOR_SEARCH_ENABLED` defaults true when Turso configured, false otherwise
- D-23: Endpoints documented `[experimental]` in OpenAPI with beta badge
- D-24: CHANGELOG and README note beta status
- D-25: Beta means flagged, not hidden - endpoints visible and testable

### Claude's Discretion
- Exact sentence-transformers loading pattern (lazy vs eager at startup)
- Background task queue implementation (FastAPI BackgroundTasks vs separate worker)
- DiskANN build parameters (`max_neighbors`, `search_l`, etc.)
- Test strategy for Turso-only features
- Re-indexing endpoint request/response shape
- Index maintenance cadence (rebuild on model change, vacuum)

### Deferred Ideas (OUT OF SCOPE)
- Real-time embedding updates over WebSocket
- Multi-language embedding models (English only in v1)
- Cross-encoder re-ranking after retrieval
- Hybrid BM25 + vector search
- Vector quantization (int8, binary)

## Project Constraints (from CLAUDE.md)

- Slow, clean, small steps - no large refactors in a single task
- Python 3.11+, FastAPI, SQLite - stack is locked
- Repository pattern + service layer - routes delegate to services
- Structured logging via `structlog` with `trace_id` binding on background tasks
- Env vars prefixed `AGENTHUB_`
- Must maintain existing API contracts (agents are in production)
- RFC 7807 Problem Details for errors
- No em dashes in any output (hyphens, colons, commas only)
- GSD workflow enforcement - file edits go through GSD commands

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VEC-01 | Turso/libSQL native vector columns (F32_BLOB) replacing zvec | Section 1 (F32_BLOB syntax), Section 3 (Alembic migration) |
| VEC-02 | Vector similarity search using `vector_distance_cos` | Section 1 (query syntax with `vector_top_k` / `vector_distance_cos`) |
| VEC-03 | DiskANN indexing for ANN search | Section 1 (`libsql_vector_idx` with metric=cosine), Section 3 (index creation in migration) |
| VEC-04 | Auto-indexing hooks on write paths | Section 4 (FastAPI BackgroundTasks pattern) + Section 2 (EmbeddingService) |
| VEC-05 | Vector search API endpoints (search, index, delete) | Section 6 (API surface design), Section 2 (service layer) |
| VEC-06 | Feature flag as opt-in beta | Section 6 (503 degradation pattern) + D-22..D-25 |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| libsql-experimental | already installed | Turso/libSQL Python driver | Already imported and used in `app/database/connection.py`. Remote-only mode works today. |
| sentence-transformers | 3.3.1 (verify with `pip index versions sentence-transformers`) | Local embeddings (default backend) | De facto standard for local embedding in Python; `all-MiniLM-L6-v2` is the benchmark small model |
| torch | 2.x (transitive via sentence-transformers) | ML backend | Required by sentence-transformers; CPU-only wheel is ~200MB |
| openai | 1.x (verify latest) | OpenAI embeddings backend | Official SDK, has built-in retry with exponential backoff, AsyncOpenAI client for async |
| tenacity | optional | Retry decorator for custom backoff | Used by OpenAI Cookbook for embedding retry patterns; alternative to SDK built-in retries |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| alembic | 1.12.1 (already installed) | Schema migration | For adding F32_BLOB columns and DiskANN index |
| pydantic | 2.4.2 (already installed) | Request/response models | For `SearchRequest`, `SearchHit`, `ReindexRequest` |
| structlog | 23.2.0 (already installed) | Background task logging with trace_id | Every embedding attempt logs with trace_id matching write request |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Turso native F32_BLOB | sqlite-vec extension | Rejected - Turso is already the chosen DB, and sqlite-vec requires extension loading that libsql handles differently. Locked by D-06. |
| sentence-transformers | fastembed (ONNX-based, smaller) | Faster cold start, no torch dependency. Rejected for v1 because sentence-transformers is more widely understood and model choice is bigger; revisit if cold start becomes a problem. |
| FastAPI BackgroundTasks | APScheduler / Celery / separate worker | Heavier, introduces new infra. BackgroundTasks is sufficient because embedding is best-effort and can retry on a timer. |
| text-embedding-3-small | text-embedding-3-large (3072 dim) | Larger is 2x more expensive and doubles storage. Small is the correct v1 default per current OpenAI guidance. |

**Version verification commands:**
```bash
pip index versions sentence-transformers
pip index versions openai
pip index versions libsql-experimental
```
Run these in Plan 01 (stack install) before pinning in `requirements.txt`.

## Architecture Patterns

### Recommended Project Structure
```
app/
├── services/
│   ├── embedding_service.py        # NEW - pluggable local/OpenAI backend
│   ├── vector_search_service.py    # NEW - wraps Turso vector_top_k queries
│   └── embedding_retry_worker.py   # NEW - background retry loop (runs in lifespan)
├── api/
│   ├── routes_search.py            # NEW - POST /v1/search unified endpoint
│   ├── routes_memory.py            # MODIFIED - add BackgroundTasks for auto-index + replace search
│   ├── routes_tasks.py             # MODIFIED - BackgroundTasks on create/complete
│   ├── routes_artifacts.py         # MODIFIED - BackgroundTasks on upload
│   └── routes_messaging.py         # MODIFIED - BackgroundTasks on send
├── models/
│   └── vector_search.py            # NEW - SearchRequest, SearchHit, ReindexRequest
└── database/
    └── vector_availability.py      # NEW - is_vector_enabled() check used by all routes
alembic/versions/
└── 0003_vector_columns.py          # NEW - F32_BLOB migration
```

### Pattern 1: Pluggable Embedding Service with Lazy Model Load
**What:** Single `EmbeddingService` interface, concrete backends picked via env var, model loaded on first call (not at startup) to keep cold start fast.
**When to use:** Anywhere code needs an embedding - both auto-index background tasks and the search query path.

```python
# app/services/embedding_service.py
# Source: sentence-transformers docs (sbert.net) + OpenAI Python SDK docs

from typing import List, Optional, Protocol
import asyncio
from openai import AsyncOpenAI
from ..config import get_settings
from ..logging import get_logger

logger = get_logger(__name__)


class EmbeddingBackend(Protocol):
    dim: int
    model_name: str
    async def embed(self, texts: List[str]) -> List[List[float]]: ...


class LocalSentenceTransformerBackend:
    dim = 384
    model_name = "sentence-transformers/all-MiniLM-L6-v2"

    def __init__(self) -> None:
        self._model = None  # Lazy load
        self._lock = asyncio.Lock()

    async def _ensure_model(self):
        if self._model is None:
            async with self._lock:
                if self._model is None:
                    # Import inside to avoid import cost if OpenAI backend used
                    from sentence_transformers import SentenceTransformer
                    # Run blocking load in threadpool
                    loop = asyncio.get_event_loop()
                    self._model = await loop.run_in_executor(
                        None,
                        lambda: SentenceTransformer(self.model_name)
                    )
                    logger.info("embedding_model_loaded", model=self.model_name)

    async def embed(self, texts: List[str]) -> List[List[float]]:
        await self._ensure_model()
        # encode() is CPU-bound blocking - run in threadpool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self._model.encode(texts, convert_to_numpy=True).tolist()
        )
        return result


class OpenAIBackend:
    dim = 1536
    model_name = "text-embedding-3-small"

    def __init__(self, api_key: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key, max_retries=3)

    async def embed(self, texts: List[str]) -> List[List[float]]:
        resp = await self._client.embeddings.create(
            model=self.model_name,
            input=texts,
        )
        return [item.embedding for item in resp.data]


def get_embedding_service() -> Optional[EmbeddingBackend]:
    settings = get_settings()
    provider = getattr(settings, "embedding_provider", "local")
    if provider == "openai":
        key = getattr(settings, "openai_api_key", None)
        if not key:
            logger.warning("embedding_provider_openai_missing_key_disabled")
            return None
        return OpenAIBackend(key)
    return LocalSentenceTransformerBackend()
```

Key design points:
- `async def embed()` even for local backend - wraps blocking work in `run_in_executor` so FastAPI event loop stays responsive
- Lock around lazy load so concurrent first-requests do not double-load the model
- OpenAI uses `AsyncOpenAI` with built-in `max_retries=3` (exponential backoff is automatic)
- Return `None` instead of raising when provider unconfigured - caller decides whether to 503

### Pattern 2: Vector Search Service with JSON-String Binding
**What:** Turso accepts vector parameters as JSON-string-wrapped-in-`vector32()`, not raw bytes. This is the single most important implementation fact.
**When to use:** Every INSERT, UPDATE, and WHERE-clause use of a vector parameter.

```python
# app/services/vector_search_service.py
# Source: https://docs.turso.tech/features/ai-and-embeddings
# Source: https://turso.tech/blog/how-to-generate-and-store-openai-vector-embeddings-with-turso

import json
from typing import List, Dict, Any, Optional
from ..database.connection import get_database
from ..logging import get_logger

logger = get_logger(__name__)

# Map entity type -> (table, content column, id column)
ENTITY_CONFIG = {
    "memory":   ("shared_memory", "value",       "id"),
    "task":     ("tasks",         "description", "id"),
    "artifact": ("artifacts",     "content",     "id"),
    "message":  ("messages",      "content",     "id"),
}


class VectorSearchService:
    def __init__(self, db):
        self.db = db

    def write_embedding(self, entity_type: str, entity_id: str,
                         vector: List[float], model_name: str) -> None:
        """Store embedding on an existing row. vector is List[float]."""
        table, _, id_col = ENTITY_CONFIG[entity_type]
        # vector32(?) SQL wrapper converts JSON array string to F32_BLOB
        query = f"""
            UPDATE {table}
            SET embedding = vector32(:vec),
                embedding_model = :model,
                embedding_status = 'ok',
                embedded_at = CURRENT_TIMESTAMP
            WHERE {id_col} = :id
        """
        self.db.execute(query, {
            "vec": json.dumps(vector),   # CRITICAL: JSON string, not bytes
            "model": model_name,
            "id": entity_id,
        })

    def mark_failed(self, entity_type: str, entity_id: str, error: str) -> None:
        table, _, id_col = ENTITY_CONFIG[entity_type]
        self.db.execute(
            f"UPDATE {table} SET embedding_status='failed', embedding_error=:err WHERE {id_col}=:id",
            {"err": error[:500], "id": entity_id}
        )

    def search_entity(self, entity_type: str, query_vector: List[float],
                       top_k: int = 10, filters: Optional[Dict[str, Any]] = None
                       ) -> List[Dict[str, Any]]:
        table, content_col, id_col = ENTITY_CONFIG[entity_type]
        index_name = f"idx_{table}_embedding"

        # vector_top_k returns (id, distance) rows - join back to table
        # vector_distance_cos then gives the similarity distance for ranking
        sql = f"""
            SELECT t.{id_col}  AS id,
                   t.{content_col} AS content,
                   vector_distance_cos(t.embedding, vector32(:qvec)) AS distance
            FROM vector_top_k(:idx, vector32(:qvec), :k) AS v
            JOIN {table} t ON t.rowid = v.id
            WHERE t.embedding_status = 'ok'
            ORDER BY distance ASC
        """
        rows = self.db.fetch_all(sql, {
            "qvec": json.dumps(query_vector),
            "idx": index_name,
            "k": top_k,
        })
        return [{"entity_type": entity_type, **r} for r in rows]
```

Key design points:
- Parameter value is always `json.dumps(list_of_floats)` wrapped in `vector32(?)` in the SQL
- `vector_top_k` is a table-valued function - it returns rowid, you JOIN back to get content
- Score column is the cosine distance (0 = identical, 2 = opposite), **sort ASC**
- Filters (owner_agent_id, created_after, etc.) go into the WHERE clause AFTER the vector_top_k call to avoid breaking index usage

### Pattern 3: FastAPI BackgroundTasks Auto-Indexing
**What:** The write endpoint returns HTTP 201 immediately and schedules an embedding task that runs on the same event loop after the response is sent.
**When to use:** Every create/update handler for the 4 indexed entity types.

```python
# app/api/routes_memory.py (relevant slice)
# Source: https://fastapi.tiangolo.com/tutorial/background-tasks/

from fastapi import BackgroundTasks, Depends
from ..services.embedding_service import get_embedding_service
from ..services.vector_search_service import VectorSearchService
from ..database.vector_availability import is_vector_enabled

async def _embed_and_store(
    entity_type: str,
    entity_id: str,
    text: str,
    trace_id: str,
) -> None:
    """Background task - never raises. Logs + marks failed on error."""
    import structlog
    log = structlog.get_logger(__name__).bind(
        trace_id=trace_id,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    db = get_database()
    svc = VectorSearchService(db)
    backend = get_embedding_service()
    if backend is None:
        log.warning("embedding_skipped_no_backend")
        return
    try:
        [vec] = await backend.embed([text])
        svc.write_embedding(entity_type, entity_id, vec, backend.model_name)
        log.info("embedding_stored", dim=len(vec))
    except Exception as e:
        log.error("embedding_failed", error=str(e))
        svc.mark_failed(entity_type, entity_id, str(e))


@router.post("/write")
async def write_memory(
    body: MemoryWrite,
    background_tasks: BackgroundTasks,
    key_info: ApiKeyAuth,
    database: Database = Depends(get_database),
):
    # ... existing insert logic returns mem_id ...
    if is_vector_enabled():
        import structlog
        trace_id = structlog.contextvars.get_contextvars().get("trace_id", "")
        background_tasks.add_task(
            _embed_and_store, "memory", mem_id, body.value, trace_id
        )
    return {"status": "created", "key": body.key, "id": mem_id}
```

Key design points:
- `BackgroundTasks` runs after response is sent but in the same event loop - safe for async work
- The background coroutine **must not raise** - catch all exceptions and record failure state
- Trace ID is captured from contextvars BEFORE scheduling the task (contextvars don't auto-propagate across task boundaries reliably)
- `is_vector_enabled()` short-circuits on local SQLite so writes stay free of background overhead

### Pattern 4: Graceful 503 for Local SQLite
**What:** A single predicate + dependency that every vector route uses.

```python
# app/database/vector_availability.py
from fastapi import HTTPException
from .connection import get_database
from ..config import get_settings

def is_vector_enabled() -> bool:
    settings = get_settings()
    if not getattr(settings, "vector_search_enabled", False):
        return False
    db = get_database()
    return db._use_turso  # private but stable

def require_vector() -> None:
    """FastAPI dependency - use in vector route signatures."""
    if not is_vector_enabled():
        # RFC 7807 Problem Details per phase 1 convention
        raise HTTPException(
            status_code=503,
            detail={
                "type": "https://openhub.dev/problems/vector-unavailable",
                "title": "Vector search unavailable",
                "status": 503,
                "detail": "Vector search requires Turso configuration. Set AGENTHUB_TURSO_DATABASE_URL and AGENTHUB_TURSO_AUTH_TOKEN.",
            },
        )
```

### Anti-Patterns to Avoid
- **Loading sentence-transformers at app startup in lifespan**: adds 2-5s to cold start even for OpenAI users. Lazy-load on first embed call instead.
- **Eager torch import at module top**: `from sentence_transformers import SentenceTransformer` at module top pulls in torch (~200MB) for every app startup. Import inside the method.
- **Using `struct.pack` for Turso vectors**: this is the sqlite-vec pattern. Turso native uses `vector32(json_string)`. Mixing them silently stores wrong data.
- **Running embedding inside the request handler**: `await backend.embed(...)` on the hot path adds 50-200ms per write. Use BackgroundTasks.
- **Filtering before vector_top_k**: `WHERE owner_agent_id = ? AND ... vector_top_k(...)` may skip the index. Filter AFTER vector_top_k in the outer query.
- **Forgetting to handle vector_top_k's rowid join**: it returns `id` meaning `rowid`, not your TEXT primary key - join on `t.rowid = v.id`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ANN search over millions of rows | Custom cosine loop in Python | `vector_top_k` + `libsql_vector_idx` DiskANN | DiskANN is the production-grade ANN index; custom Python is O(n) and will melt |
| OpenAI retry/backoff | Custom tenacity wrapper | `AsyncOpenAI(max_retries=3)` SDK built-in | SDK already handles 429/5xx with exponential backoff |
| Text chunking for long inputs | Ad-hoc split() | OpenAI cookbook `embedding_long_inputs` pattern (truncate or chunk-and-average) | Edge cases (UTF-8 boundaries, token counting) are error-prone |
| Embedding cache / deduplication | In-memory dict | Skip entirely for v1 - rely on `embedding_status='ok'` check | Premature optimization; re-embedding same text is cheap |
| Vector serialization | `struct.pack('f'*n, *vec)` | `vector32(json.dumps(vec))` | Turso's documented Python path is JSON string; bytes path is sqlite-vec |
| Background task scheduler | Celery / APScheduler | `FastAPI BackgroundTasks` + one asyncio timer loop in lifespan for 5-min retry | v1 scale is low; heavier infra can wait until a second worker process is needed |

**Key insight:** Most of this phase is plumbing, not algorithms. The temptation is to hand-roll vector math "because it's just dot products" - don't. DiskANN + `vector_top_k` is the entire value proposition of Turso native vectors.

## Runtime State Inventory

This phase is additive (new columns, new endpoints) so most categories are empty, but two items need attention.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Existing `shared_memory`, `tasks`, `artifacts`, `messages` rows have NO embeddings. After migration they will have `embedding_status = NULL`. | Data backfill task: run the re-index endpoint (D-15) against existing rows. Document as manual post-deploy step OR include a startup backfill toggle. |
| Live service config | `zvec_path` env var (`AGENTHUB_ZVEC_PATH`) is set in some environments pointing to `./data/zvec`. | Code edit: remove `zvec_path` field from `Settings` in `app/config.py`, remove `zvec==0.1.0` from `requirements.txt`, delete the data dir creation logic if any. |
| OS-registered state | None - no systemd/scheduler entries reference vector state | None - verified by inspection |
| Secrets/env vars | NEW: `AGENTHUB_OPENAI_API_KEY` needs to be added to `Settings` + documented. `AGENTHUB_EMBEDDING_PROVIDER`, `AGENTHUB_VECTOR_SEARCH_ENABLED` also new. | Code edit: add 3 new fields to `Settings`. Document in README and `.env.example`. |
| Build artifacts / installed packages | zvec Python package is installed but will become orphaned. | Remove from `requirements.txt`; add migration note for existing deployments to `pip uninstall zvec` (non-critical since import-on-demand). |

**The canonical question:** After every file in the repo is updated, what runtime systems still have the old string cached, stored, or registered?

Answer: existing Turso deployments (e.g. `hub.brunhilde.cloud` per user memory) will have tables without the new `embedding` columns until the migration runs. Plan must ensure the migration is idempotent and safe to run against a live DB with existing rows.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | All | YES | 3.12.3 (WSL local) | - |
| libsql-experimental | DB driver (existing) | YES | already in requirements.txt | sqlite3 fallback (vector features disabled) |
| Turso cloud DB | Vector feature runtime | Conditional | - | Local SQLite -> 503 on vector endpoints (per D-08) |
| sentence-transformers | Default embedding backend | TO INSTALL | verify latest in Plan 01 | OpenAI backend if API key present |
| torch (transitive) | sentence-transformers runtime | TO INSTALL with above | CPU wheel ~200MB | Skip local embeddings, require OpenAI |
| openai (Python SDK) | OpenAI backend | TO INSTALL | verify latest | Local backend is default anyway |
| alembic | Migration runner | YES | 1.12.1 | - |

**Missing dependencies with no fallback:**
- Turso DB credentials for live vector testing - must be either provided by user or the phase's integration tests are marked `@pytest.mark.turso` and skipped locally.

**Missing dependencies with fallback:**
- sentence-transformers / torch: if the OSS user does not want to install ~300MB of ML deps, they can set `AGENTHUB_EMBEDDING_PROVIDER=openai` and only pip-install `openai`. Plan should keep sentence-transformers in an extras group (`requirements-vector.txt` or `pyproject.toml` optional-dependencies) so bare install stays lean.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.4.3 + pytest-asyncio 0.21.1 |
| Config file | `pyproject.toml` (pytest section), `tests/conftest.py` (session fixtures) |
| Quick run command | `pytest tests/unit/test_embedding_service.py -x` |
| Full suite command | `pytest --tb=short -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VEC-01 | Migration adds F32_BLOB columns and is idempotent | integration | `pytest tests/integration/test_vector_migration.py -x` | NO - Wave 0 |
| VEC-01 | zvec removed from requirements | smoke | `pytest tests/unit/test_vector_deps.py -k no_zvec -x` | NO - Wave 0 |
| VEC-02 | EmbeddingService local backend returns 384-dim vectors | unit | `pytest tests/unit/test_embedding_service.py::test_local_dim -x` | NO - Wave 0 |
| VEC-02 | EmbeddingService OpenAI backend returns 1536-dim (mocked) | unit | `pytest tests/unit/test_embedding_service.py::test_openai_dim_mocked -x` | NO - Wave 0 |
| VEC-02 | VectorSearchService writes + reads embedding roundtrip | integration | `pytest tests/integration/test_vector_search.py::test_roundtrip -x` (Turso only, marked) | NO - Wave 0 |
| VEC-02 | Distance ordering matches expected nearest-neighbor | integration | `pytest tests/integration/test_vector_search.py::test_ranking -x` (Turso only) | NO - Wave 0 |
| VEC-03 | DiskANN index exists after migration | integration | `pytest tests/integration/test_vector_migration.py::test_index_created -x` (Turso only) | NO - Wave 0 |
| VEC-04 | Write endpoint schedules background embedding | unit | `pytest tests/unit/test_auto_index.py::test_background_task_scheduled -x` (mock backend) | NO - Wave 0 |
| VEC-04 | Failed embedding leaves row with status=failed | unit | `pytest tests/unit/test_auto_index.py::test_failed_status -x` | NO - Wave 0 |
| VEC-04 | Retry worker re-processes failed rows | unit | `pytest tests/unit/test_retry_worker.py -x` | NO - Wave 0 |
| VEC-05 | POST /v1/search returns 503 on local SQLite | integration | `pytest tests/integration/test_search_api.py::test_503_local -x` | NO - Wave 0 |
| VEC-05 | POST /v1/search honors top_k limit | integration | `pytest tests/integration/test_search_api.py::test_top_k_cap -x` | NO - Wave 0 |
| VEC-05 | Per-entity shortcut delegates to unified | integration | `pytest tests/integration/test_search_api.py::test_shortcut_delegation -x` | NO - Wave 0 |
| VEC-06 | Feature flag disables endpoints when set false | integration | `pytest tests/integration/test_search_api.py::test_flag_off -x` | NO - Wave 0 |
| VEC-06 | OpenAPI marks endpoints [experimental] | smoke | `pytest tests/integration/test_search_api.py::test_openapi_beta_tag -x` | NO - Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/unit/test_embedding_service.py tests/unit/test_auto_index.py tests/unit/test_retry_worker.py -x` (unit tests only, ~5s)
- **Per wave merge:** `pytest tests/unit tests/integration/test_vector_migration.py tests/integration/test_search_api.py -x --tb=short -q`
- **Phase gate:** Full suite green (including Turso-marked tests against live Turso test DB OR explicitly skipped with reason logged)

### Wave 0 Gaps
- [ ] `tests/unit/test_embedding_service.py` - local backend dim test, OpenAI backend mocked test, provider selection test
- [ ] `tests/unit/test_auto_index.py` - BackgroundTasks scheduling test with mock backend, failed-status test
- [ ] `tests/unit/test_retry_worker.py` - worker picks up failed rows and re-embeds
- [ ] `tests/unit/test_vector_deps.py` - asserts zvec is NOT in installed deps
- [ ] `tests/integration/test_vector_migration.py` - runs alembic upgrade, checks columns exist; Turso-marked test checks index
- [ ] `tests/integration/test_vector_search.py` - marked `@pytest.mark.turso`, skipped if `TURSO_DATABASE_URL` not set (see "Test Strategy" section below)
- [ ] `tests/integration/test_search_api.py` - 503 test, top_k cap, shortcut delegation, flag off, OpenAPI beta tag
- [ ] `tests/conftest.py` - add `turso` pytest mark with skip-if-not-configured logic, add `mock_embedding_backend` fixture

## Pitfalls and Gotchas

### Pitfall 1: `vector32(?)` parameter format is undocumented for Python
**What goes wrong:** Developer assumes Python driver accepts `list[float]` or `bytes` directly; stores garbage.
**Why it happens:** Turso docs show SQL and JS examples; Python examples are thin. sqlite-vec docs show `struct.pack` and developers copy-paste.
**How to avoid:** Always pass `json.dumps(vector)` as a string parameter bound to a SQL expression `vector32(?)`. Write an integration smoke test early (Plan 01 or 02) that inserts a known vector, reads it back via `vector_distance_cos(vector32('[...]'), embedding)`, and asserts distance is 0.
**Warning signs:** Search returns no results even with seeded data; `vector_top_k` returns rows but distances are nonsensical (> 2 or NaN).

### Pitfall 2: DiskANN index DDL fails on local SQLite
**What goes wrong:** `CREATE INDEX ... libsql_vector_idx(...)` is a libSQL-only SQL extension. Plain sqlite3 raises `no such function: libsql_vector_idx`.
**Why it happens:** Alembic runs the same migration regardless of backend.
**How to avoid:** Wrap the index DDL in a runtime check: `if op.get_bind().dialect.name contains 'libsql' OR env var set`, then execute. Use `CREATE INDEX IF NOT EXISTS` to stay idempotent. Alternatively, move index creation out of Alembic into a one-time script that runs on Turso only.
**Warning signs:** Local dev broken after migration; CI fails on SQLite test runner.

### Pitfall 3: Lazy model load serializes all requests
**What goes wrong:** First concurrent burst of writes all wait on a single asyncio.Lock while the model loads.
**Why it happens:** `SentenceTransformer(model_name)` takes 1-3s; if N requests arrive in parallel, N-1 wait.
**How to avoid:** This is acceptable for v1 (writes are background anyway). If problematic later, pre-warm via a throwaway `embed(['warmup'])` call scheduled at lifespan startup as an asyncio.task (not awaited).
**Warning signs:** First request after restart takes several seconds to return.

### Pitfall 4: sentence-transformers + uvicorn workers fork issue
**What goes wrong:** When uvicorn runs with `--workers N > 1`, each worker forks AFTER the model is loaded in the parent. PyTorch models are not fork-safe; seg faults or deadlocks.
**Why it happens:** Torch uses threads and shared memory that don't survive fork.
**How to avoid:** Lazy-load AFTER workers fork (which is what the pattern above does). Never load in a module-level global. Also set `TOKENIZERS_PARALLELISM=false` to silence a related HF warning.
**Warning signs:** Multi-worker deployments crash on first embedding; single-worker works fine.

### Pitfall 5: `rowid` vs `id` in vector_top_k
**What goes wrong:** `vector_top_k` returns an `id` column that is the SQLite `rowid`, NOT the entity's TEXT primary key. Naive `JOIN t ON t.id = v.id` silently returns zero rows.
**Why it happens:** libSQL's vector index is keyed on rowid internally.
**How to avoid:** Always join `ON t.rowid = v.id`. Return `t.id` in the SELECT list to get the TEXT primary key.
**Warning signs:** Search returns empty results even though data exists; SELECT without join shows rows.

### Pitfall 6: Background task crashes invisibly
**What goes wrong:** Exception inside a `BackgroundTasks` coroutine is swallowed. The write endpoint returns 201 but no embedding ever appears, and there's no log.
**Why it happens:** FastAPI BackgroundTasks do not re-raise to the caller.
**How to avoid:** Wrap the entire background coroutine body in `try/except Exception` and log+mark-failed on any error. Add a metric counter (Prometheus) for `embedding_background_failures_total`.
**Warning signs:** Users report "my data isn't searchable" but no error logs; `SELECT COUNT(*) WHERE embedding IS NULL` is growing.

### Pitfall 7: OpenAI text length > 8192 tokens
**What goes wrong:** Large artifacts or long task outputs exceed `text-embedding-3-small`'s 8192 token input limit. API returns 400.
**Why it happens:** Content is arbitrary length.
**How to avoid:** Truncate to ~7500 tokens before sending (~30KB chars as safe bound). For v1, this is acceptable loss. Document as a known limitation.
**Warning signs:** Large-content entities consistently end up with `embedding_status='failed'` and a `max_tokens` error message.

### Pitfall 8: Model dimension mismatch after provider switch
**What goes wrong:** Developer switches `AGENTHUB_EMBEDDING_PROVIDER` from local (384) to OpenAI (1536). All subsequent writes fail because the column is `F32_BLOB(384)`.
**Why it happens:** D-05 is explicit but easy to forget in operations.
**How to avoid:** Store `embedding_model` per row; at search time, filter to rows matching the query's model. On startup, compare configured provider dim against column dim and refuse to start with a loud error if mismatched without `AGENTHUB_ALLOW_DIM_MISMATCH=1`.
**Warning signs:** After provider switch, all new writes have `embedding_status='failed'` with "dimension mismatch" errors.

## Code Examples

Verified patterns from official sources.

### Creating vector columns + index (Alembic migration)
```python
# alembic/versions/0003_vector_columns.py
# Source: https://docs.turso.tech/features/ai-and-embeddings
from alembic import op

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None

VEC_DIM = 384  # sentence-transformers/all-MiniLM-L6-v2 default

def upgrade() -> None:
    # F32_BLOB(n) is accepted by SQLite as just BLOB with a type affinity hint
    # - safe on both libsql and vanilla sqlite3. The index DDL is libsql-only.

    for table in ["shared_memory", "tasks", "artifacts", "messages"]:
        # Columns - safe on all backends
        op.execute(f"ALTER TABLE {table} ADD COLUMN embedding F32_BLOB({VEC_DIM})")
        op.execute(f"ALTER TABLE {table} ADD COLUMN embedding_model TEXT")
        op.execute(f"ALTER TABLE {table} ADD COLUMN embedding_status TEXT")
        op.execute(f"ALTER TABLE {table} ADD COLUMN embedding_error TEXT")
        op.execute(f"ALTER TABLE {table} ADD COLUMN embedded_at TIMESTAMP")

    # DiskANN index - libsql only, guard at runtime
    bind = op.get_bind()
    # Heuristic: libsql dialect reports as sqlite but the function exists only on libsql.
    # Try/except keeps local sqlite tests happy.
    for table in ["shared_memory", "tasks", "artifacts", "messages"]:
        try:
            op.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{table}_embedding "
                f"ON {table}(libsql_vector_idx(embedding, 'metric=cosine'))"
            )
        except Exception as e:
            # Local sqlite will fail here - that's expected per D-08
            import logging
            logging.getLogger(__name__).warning(
                f"vector_index_skip table={table} reason={e}"
            )

def downgrade() -> None:
    # SQLite does not support DROP COLUMN easily; drop indexes only
    for table in ["shared_memory", "tasks", "artifacts", "messages"]:
        op.execute(f"DROP INDEX IF EXISTS idx_{table}_embedding")
```

### Unified search endpoint
```python
# app/api/routes_search.py
# Source: decisions D-16..D-21
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from ..database.vector_availability import require_vector
from ..services.embedding_service import get_embedding_service
from ..services.vector_search_service import VectorSearchService, ENTITY_CONFIG
from ..database.connection import get_database

router = APIRouter(prefix="/v1/search", tags=["search [experimental]"])

DEFAULT_TYPES = list(ENTITY_CONFIG.keys())


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=5000)
    types: Optional[List[str]] = Field(default=None)
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict)
    top_k: int = Field(default=10, ge=1, le=50)


class SearchHit(BaseModel):
    entity_type: str
    id: str
    content: str
    distance: float


@router.post("", response_model=List[SearchHit], dependencies=[Depends(require_vector)])
async def unified_search(req: SearchRequest):
    backend = get_embedding_service()
    if backend is None:
        raise HTTPException(503, "embedding backend unavailable")

    [qvec] = await backend.embed([req.query])

    types = req.types or DEFAULT_TYPES
    svc = VectorSearchService(get_database())
    all_hits: List[Dict[str, Any]] = []
    for t in types:
        all_hits.extend(svc.search_entity(t, qvec, top_k=req.top_k, filters=req.filters))

    # Cross-entity merge by distance ascending, cap at top_k
    all_hits.sort(key=lambda h: h["distance"])
    return all_hits[:req.top_k]
```

## Test Strategy (Turso-only features)

The core tension: integration tests for `vector_top_k` / `libsql_vector_idx` **cannot run on vanilla SQLite**. Three possible approaches:

### Approach A: Mark-and-skip (RECOMMENDED for v1)
- Add a `pytest.mark.turso` marker in `conftest.py`
- Marker skips the test if `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` are not set
- CI pipeline has two jobs: (1) standard unit + non-vector integration runs on every PR, (2) `pytest -m turso` runs on a dedicated test-Turso DB triggered on main branch pushes
- Local developer can run vector tests by exporting credentials to a personal dev Turso DB

```python
# tests/conftest.py additions
import os, pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "turso: requires live Turso DB for vector tests")

def pytest_collection_modifyitems(config, items):
    if os.environ.get("TURSO_DATABASE_URL") and os.environ.get("TURSO_AUTH_TOKEN"):
        return
    skip_turso = pytest.mark.skip(reason="Turso credentials not set")
    for item in items:
        if "turso" in item.keywords:
            item.add_marker(skip_turso)
```

### Approach B: Mock the entire vector layer
- Define a `VectorStore` protocol; real implementation uses libsql, test implementation uses in-memory dict + numpy cosine
- Unit tests use the mock; no Turso needed
- Downside: you never actually exercise the real SQL syntax - a typo in `vector_top_k` goes undetected

### Approach C: Run sqld (libsql server) in a test container
- Start `sqld` in a Docker sidecar for integration tests
- `sqld` is the open-source server that backs Turso - supports the same vector extensions
- Downside: adds container management to test setup, slower CI

**Recommendation:** Approach A for v1, combined with a minimal mock backend for unit tests of the embedding/search service wiring (Approach B layered on top for speed). Consider Approach C post-v1 if vector test coverage becomes critical.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate vector DB (Pinecone, Weaviate, Chroma) | Native vector columns in primary DB (Turso, pgvector, SQLite vec) | 2024 onwards | "You don't need a separate vector DB" - massively simpler ops for small-medium scale |
| zvec library for SQLite vectors | Turso F32_BLOB + vector_top_k | 2024 (Turso native support) | Locked by VEC-01; zvec is deprecated in this codebase |
| sync OpenAI client with manual retry | `AsyncOpenAI(max_retries=N)` | openai-python 1.x | Built-in exponential backoff |
| text-embedding-ada-002 (1536 dim, $0.0001/1k tok) | text-embedding-3-small (1536 dim, $0.00002/1k tok) | Jan 2024 | 5x cheaper, higher MTEB scores |
| Eager-load all ML models at startup | Lazy load on first request | Long-standing best practice for cold-start-sensitive services | Faster boot, especially for multi-worker deployments |

**Deprecated/outdated:**
- `zvec` package: replace with Turso native F32_BLOB per D-10
- `libsql-client` Python: there are two libraries (`libsql-experimental-python` and `libsql-python`); this codebase already uses `libsql-experimental`; do not mix
- `text-embedding-ada-002`: use text-embedding-3-small for any new OpenAI work

## Open Questions

1. **Does `libsql-experimental-python` accept bytes parameters for BLOB columns, or strictly JSON-via-`vector32()`?**
   - What we know: Turso docs show SQL with `vector32('[...]')` literals. JS/TS blog posts show `new Float32Array(embedding).buffer` as an ArrayBuffer parameter. Python docs are silent.
   - What's unclear: whether `db.execute("INSERT INTO t VALUES (?)", (struct.pack(...),))` works as an alternative.
   - Recommendation: Plan 02 (EmbeddingService + smoke test) should include a 10-minute spike that tries both paths against a real Turso DB and locks the working one. Default to `vector32(json.dumps(...))` since it is the documented SQL-side approach and works uniformly across languages.

2. **Does the project's existing Turso deployment have write access for Alembic migrations from the app process?**
   - What we know: `app/main.py` runs DDL in lifespan currently. Alembic was added in Phase 1.
   - What's unclear: whether the production Turso auth token has full DDL rights or only DML.
   - Recommendation: Plan the migration to be runnable via `alembic upgrade head` from a dev machine with elevated credentials, not from the app process on first boot.

3. **Should the 5-minute retry worker run as an asyncio task in the main app lifespan, or as a separate command (`python -m app.workers.embedding_retry`)?**
   - What we know: D-13 specifies "every 5 min" retry. `app/services/connection_manager.py` (from Phase 2) uses the asyncio-task-in-lifespan pattern.
   - What's unclear: whether multiple workers would race each other if the hub is ever scaled horizontally.
   - Recommendation: Start with the in-lifespan asyncio task pattern matching Phase 2 convention. Add a `SELECT ... FOR UPDATE SKIP LOCKED` equivalent only if horizontal scaling is introduced (not in v1).

4. **How large is the full sentence-transformers install?**
   - What we know: model weights ~90MB, torch CPU wheel ~200MB, transformers + deps ~50MB. Total ~350MB.
   - What's unclear: whether this is acceptable for the "5-minute quickstart" OSS goal (OSS-01).
   - Recommendation: Put sentence-transformers and torch in an optional dependency group (`pip install openhub[vector]`). Bare `pip install openhub` works, vector endpoints return 503 "embeddings backend not installed".

## Sources

### Primary (HIGH confidence)
- [Turso AI & Embeddings docs](https://docs.turso.tech/features/ai-and-embeddings) - F32_BLOB syntax, vector32(), vector_distance_cos, libsql_vector_idx, vector_top_k
- [sentence-transformers all-MiniLM-L6-v2 model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) - 384 dim, ~90MB, ~43MB VRAM for inference
- [sentence-transformers efficiency docs](https://sbert.net/docs/sentence_transformer/usage/efficiency.html) - batching and speed tradeoffs
- [FastAPI BackgroundTasks docs](https://fastapi.tiangolo.com/tutorial/background-tasks/) - add_task pattern, lifecycle
- [OpenHub app/database/connection.py] - existing Turso detection logic (lines 19-69)
- [OpenHub app/config.py] - existing Settings with embedding_model pre-configured
- [OpenHub alembic/versions/0001_initial_schema.py] - migration pattern using op.execute(...) with CREATE IF NOT EXISTS
- [OpenHub app/api/routes_memory.py] - current LIKE-based search_memory to replace

### Secondary (MEDIUM confidence)
- [Turso blog: Generating OpenAI embeddings](https://turso.tech/blog/how-to-generate-and-store-openai-vector-embeddings-with-turso) - confirms vector32(?) parameter-binding pattern (shown in TS, pattern transfers to Python)
- [OpenAI Cookbook: embedding long inputs](https://cookbook.openai.com/examples/embedding_long_inputs) - truncation and chunking for texts >8192 tokens
- [LangChain issue 36547: async embedding batches](https://github.com/langchain-ai/langchain/issues/36547) - confirms asyncio.gather pattern for concurrent batches
- [Turso blog: You don't need a separate vector DB](https://turso.tech/blog/you-dont-need-a-separate-vector-database) - rationale for native columns
- [Alex Garcia: SQL vector search in 7 languages](https://alexgarcia.xyz/blog/2024/sql-vector-search-languages/index.html) - NOTE: this is sqlite-vec, not Turso native; used to rule out the struct.pack approach

### Tertiary (LOW confidence - flagged for validation)
- Python driver parameter binding for F32_BLOB: no first-party Python example found. Validated by SQL-layer docs + cross-language consistency, but a smoke test in Plan 02 is mandatory before building on this assumption.
- [libsql issue 1903](https://github.com/tursodatabase/libsql/issues/1903) - references TS-only debugging of vector inserts; does not confirm Python path.

## Metadata

**Confidence breakdown:**
- Turso SQL syntax (F32_BLOB, vector_top_k, libsql_vector_idx, vector_distance_cos): HIGH - official docs
- Python parameter binding (`vector32(json.dumps(...))`): MEDIUM-HIGH - documented SQL pattern, cross-language consistency, no first-party Python example
- sentence-transformers lazy-load + threadpool pattern: HIGH - sbert docs + well-known asyncio pattern
- OpenAI async SDK retry behavior: HIGH - documented in openai-python README
- FastAPI BackgroundTasks lifecycle: HIGH - FastAPI docs
- Alembic migration idempotency with libSQL-only DDL: MEDIUM - tested pattern from Phase 1 applies; libsql_vector_idx DDL exception path is defensive not verified
- DiskANN parameter choice (`metric=cosine`): MEDIUM - docs show the option, optimal `max_neighbors`/`search_l` not tested

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (30 days). Turso vector features are actively evolving - recheck release notes before any major refactor of this phase's output.
