# Phase 2.4 — Vector Memory on OpenHub Events

> **For Hermes:** Use strict TDD. Add a failing test before each behavior change.

## Current State

OpenHub already has a beta vector/search stack:

- `app/api/routes_search.py`: `/v1/search`, `/v1/search/reindex`, delete embedding.
- `app/services/vector_search_service.py`: Turso `vector32(...)` / `vector_top_k(...)` wrapper.
- `app/services/embedding_service.py`: local sentence-transformers and OpenAI-compatible backends.
- `app/services/embedding_hooks.py`: safe `schedule_embedding(...)` and never-raises background `_embed_and_store(...)`.
- Existing write-path hooks already cover normal memory/task/artifact/message routes.

## Gap

ACN task creation (`POST /v1/acn/tasks`) bypasses the normal `/v1/tasks/` route, so tasks created through the agent coordination plane are not automatically scheduled for vector indexing. This weakens the command-center memory story: agent-submitted tasks are real OpenHub knowledge but do not enter the semantic search pipeline.

## First Slice

Wire ACN task creation into the existing embedding hook:

1. Add `BackgroundTasks` to `routes_acn.create_task`.
2. After `TaskService.create_task(...)`, call:
   - `schedule_embedding(background_tasks, "task", new_task.id, new_task.description)`
3. Keep the hook safe to call unconditionally; it no-ops unless Turso/vector is enabled.
4. Add an integration test proving `/v1/acn/tasks` schedules/executes embedding when vector is forced enabled with fake backend/service.

## Acceptance Criteria

- ACN task creation embeds the task description exactly once when vector is enabled.
- Local SQLite / vector disabled still stays no-op and does not break ACN task creation.
- Existing task/memory/artifact/message auto-index tests remain green.
- Full backend tests pass.
- Commit and push to `origin/master`.
