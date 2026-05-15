# Phase 2.4 — Vector Memory on OpenHub Events

> **For Hermes:** Use strict TDD. Add a failing test before each behavior change. Do not call Phase 2.4 complete from a single slice; report exact completed scope and remaining work.

## Current State

OpenHub has a beta vector/search stack:

- `app/api/routes_search.py`: `/v1/search`, `/v1/search/reindex`, delete embedding.
- `app/services/vector_search_service.py`: Turso `vector32(...)` / `vector_top_k(...)` wrapper.
- `app/services/embedding_service.py`: local sentence-transformers and OpenAI-compatible backends.
- `app/services/embedding_hooks.py`: safe `schedule_embedding(...)` and never-raises background `_embed_and_store(...)`.
- Existing write-path hooks cover normal memory/task/artifact/message routes.
- ACN/event write paths need explicit hooks because they bypass the normal CRUD routes.

## Completed Slice 1 — ACN Task Auto-indexing

Gap closed: ACN task creation (`POST /v1/acn/tasks`) bypassed the normal `/v1/tasks/` route, so agent-submitted tasks were not automatically scheduled for vector indexing.

Implemented:

1. `BackgroundTasks` added to `routes_acn.create_task`.
2. After `TaskService.create_task(...)`, ACN tasks call:
   - `schedule_embedding(background_tasks, "task", new_task.id, new_task.description)`
3. Hook remains safe to call unconditionally; it no-ops unless Turso/vector is enabled.
4. Integration test proves `/v1/acn/tasks` schedules/executes embedding when vector is forced enabled with fake backend/service.

## Completed Slice 2 — ACN Agent Registry Metadata Auto-indexing

Gap closed: ACN agent registration stores rich public registry metadata but did not enter semantic search.

Implemented:

1. `agents` now has vector metadata columns through migration `0005_agent_vector_columns.py`:
   - `embedding`
   - `embedding_model`
   - `embedding_status`
   - `embedding_error`
   - `embedded_at`
2. Search contract now includes `agent` as a valid entity type.
3. `VectorSearchService.ENTITY_CONFIG` maps `agent` to the `agents` table, while search/reindex content now uses rich public registry text rather than description alone.
4. ACN agent registration and invite-based join schedule embeddings using safe, public registry metadata text:
   - agent name
   - description
   - node
   - model/platform
   - capabilities
   - skills
   - MCP profile names
   - languages/channels
5. The text intentionally excludes credentials, callback secrets, API keys, tokens, and private runtime payloads.
6. Integration and migration tests cover the behavior.

## Completed Slice 3 — Real Turso Smoke + Sparse Agent Reindex Hardening

Gap closed: agent write-path embeddings used rich registry metadata, but reindex/retry/search content could collapse to sparse `agents.description` only.

Implemented/verified:

1. Real Turso smoke created a unique ACN agent, embedded it through the actual vector stack, and found it through `/v1/search` with `types=["agent"]`.
2. `VectorSearchService` now builds safe agent registry text for search/reindex/retry from public metadata fields.
3. Sparse-description agents still produce useful reindex content from capabilities/skills/model/platform/etc.
4. Unit coverage proves sparse agent metadata is not reduced to an empty string.

## Remaining Work — Not Yet Complete

- Optional dashboard semantic search exposure for agents/tasks if product direction wants it.
- Optional cleanup of pre-existing frontend `ResponsiveList` HTML nesting warning.

## Acceptance Criteria for Current Slice

- ACN task creation embeds the task description exactly once when vector is enabled.
- ACN agent registration embeds public metadata exactly once when vector is enabled.
- Local SQLite / vector disabled remains no-op and does not break ACN paths.
- Migration tests prove `agents` receives vector columns.
- Existing vector tests remain green.
- Full backend/frontend QA passes.
- Commit and push to `origin/master`.
