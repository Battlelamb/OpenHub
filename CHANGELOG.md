# Changelog

All notable changes to OpenHub are documented in this file.

## [Phase 3 - Vector Database] - 2026-04-13

### Added (BETA / Experimental)

- VEC-01: Turso/libSQL native vector columns (F32_BLOB) replacing zvec
- VEC-02: Semantic search via vector_distance_cos with DiskANN index lookup
- VEC-03: DiskANN indexing via libsql_vector_idx (cosine metric)
- VEC-04: Auto-indexing hooks on memory/task/artifact/message write paths (async via FastAPI BackgroundTasks) plus a 5-minute polling retry worker for failed/missing embeddings
- VEC-05: POST /v1/search unified endpoint, per-entity shortcuts (/v1/memory/search, /v1/tasks/search, /v1/artifacts/search, /v1/messages/search), admin-only POST /v1/search/reindex and DELETE /v1/search/{entity_type}/{entity_id}
- VEC-06: Opt-in beta gated by AGENTHUB_VECTOR_SEARCH_ENABLED with startup advisory log, OpenAPI BETA tag description, and full README documentation
- New settings: AGENTHUB_EMBEDDING_PROVIDER (local|openai), AGENTHUB_OPENAI_API_KEY, AGENTHUB_VECTOR_SEARCH_ENABLED
- New endpoints tagged "search [experimental]" in OpenAPI /docs so consumers can identify the beta surface

### Removed

- zvec dependency (replaced by native Turso vector columns)
- AGENTHUB_ZVEC_PATH config setting

### Notes

- Vector search requires Turso configuration. On local SQLite, all vector endpoints return RFC 7807 503 responses and the rest of OpenHub continues to work normally.
- sentence-transformers and openai are now declared in requirements.txt. The local backend is the default.
- See the README "Vector Search (Beta)" section for setup instructions, supported endpoints, and known limitations.
