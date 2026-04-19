---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Ready to execute
stopped_at: Completed 04-09-PLAN.md
last_updated: "2026-04-19T14:08:01.603Z"
progress:
  total_phases: 5
  completed_phases: 4
  total_plans: 31
  completed_plans: 31
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-07)

**Core value:** Any developer can self-host OpenHub, connect their AI agents, and coordinate multi-agent workflows from a single command center - reliably and without conflicts.
**Current focus:** Phase 04 — command-center-ui

## Current Position

Phase: 04 (command-center-ui) — EXECUTING
Plan: 4 of 9

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 01-backend-hardening P04 | 3min | 2 tasks | 5 files |
| Phase 01-backend-hardening P03 | 2min | 2 tasks | 5 files |
| Phase 01-backend-hardening P07 | 2min | 2 tasks | 16 files |
| Phase 01-backend-hardening P05 | 3min | 2 tasks | 3 files |
| Phase 01-backend-hardening P06 | 3min | 2 tasks | 7 files |
| Phase 01-backend-hardening P08 | 3min | 2 tasks | 4 files |
| Phase 02-websocket-test-suite P01 | 8min | 2 tasks | 3 files |
| Phase 02-websocket-test-suite P03 | 6min | 2 tasks | 4 files |
| Phase 02 P04 | 15min | 2 tasks | 2 files |
| Phase 02 P06 | 10m | 2 tasks | 2 files |
| Phase 03-vector-database P01 | 8m | 2 tasks | 18 files |
| Phase 03-vector-database P03 | 4m | 1 tasks | 4 files |
| Phase 03-vector-database P02 | 5m | 2 tasks | 4 files |
| Phase 03-vector-database P04 | 6m | 2 tasks | 10 files |
| Phase 03-vector-database P05 | 9m | 3 tasks | 10 files |
| Phase 03 P06 | 4m | 2 tasks | 6 files |
| Phase 04-command-center-ui P08 | 6min | 3 tasks | 9 files |
| Phase 04-command-center-ui P06 | 10min | 3 tasks | 22 files |
| Phase 04-command-center-ui P09 | 45min | 3 tasks | 10 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Roadmap: Backend hardening must precede all tests - auth stub in app/dependencies.py accepts any 8-char string, making test results meaningless until fixed
- Roadmap: WebSocket auth via initial message frame, not URL query param - prevents token exposure in logs and browser history
- Roadmap: Vector DB uses Turso/libSQL native F32_BLOB columns - not ChromaDB, not zvec; ships as opt-in beta with documented experimental status
- Roadmap: Phase 3 (Vector DB) depends only on Phase 1 - can be planned alongside Phase 2 if desired
- [Phase 01-backend-hardening]: Used raw SQL op.execute in Alembic migration for existing DB safety instead of op.create_table
- [Phase 01-backend-hardening]: CORS origins default to localhost:3000 and localhost:7788 - production must override via AGENTHUB_CORS_ORIGINS
- [Phase 01-backend-hardening]: datetime.now(timezone.utc) is the canonical timestamp pattern - all 4 high-impact files converted
- [Phase 01-backend-hardening]: datetime.now(timezone.utc) sweep complete across all 16 files - zero utcnow() remaining codebase-wide
- [Phase 01-backend-hardening]: RFC 7807 Problem Details as the standard error format - all errors use ProblemDetail model with type/title/status/detail/instance/trace_id
- [Phase 01-backend-hardening]: Limiter in dedicated app/limiter.py to avoid circular imports; RFC 7807 JSON for 429 instead of plain text; trace_id as structlog contextvars key
- [Phase 01-backend-hardening]: request parameter reordered to first position in auth routes for slowapi compatibility
- [Phase 02-websocket-test-suite]: conftest uses tempfile DB path so app lifespan os.makedirs succeeds (fixed pre-existing :memory: blocker)
- [Phase 02-websocket-test-suite]: admin_headers fixture returns real signed JWT; auth_token and agent_headers added for WS and agent-role tests
- [Phase 02-websocket-test-suite]: Mint JWT per integration test with sub=<real agent id> because get_current_agent looks up sub in the agents table
- [Phase 02-websocket-test-suite]: Rule 1 fix: TaskService fail/complete/cancel now json.dumps payload dict before sqlite update
- [Phase 02]: Plan 02-04: WS UI endpoint uses first-frame JWT auth via app.state.connection_manager, welcome envelope carries client_id in data (not agent_id), refresh via cm.refresh_ui_expiry()
- [Phase 03-vector-database]: Migration 0003: ALTER TABLE wrapped in safe_execute(ignore=duplicate column name) for idempotency since SQLite has no IF NOT EXISTS for ADD COLUMN
- [Phase 03-vector-database]: is_vector_enabled is single source of truth - downstream plans must call require_vector instead of inspecting Database._use_turso directly
- [Phase 03-vector-database]: alembic env.py overrides sqlalchemy.url from settings.db_path - migration tests must monkeypatch AGENTHUB_DB_PATH and reset cached settings
- [Phase 03-vector-database]: Plan 03-03: lazy module import inside asyncio.Lock double-check is the canonical pattern - sentence_transformers and torch must never appear in sys.modules at app boot
- [Phase 03-vector-database]: Plan 03-03: get_embedding_service returns Optional[EmbeddingBackend] - downstream plans must handle None for openai-without-key graceful degradation (D-03)
- [Phase 03-vector-database]: vector32(:vec) is bound exclusively as json.dumps(list_of_floats); raw bytes/struct.pack/numpy reject silently and break the index
- [Phase 03-vector-database]: vector_top_k joins on t.rowid (NOT t.id) and filter clauses live in outer WHERE after vector_top_k - pre-filtering bypasses DiskANN
- [Phase 03-vector-database]: Plan 03-04: schedule_embedding short-circuits at call time on is_vector_enabled - tests must monkeypatch the function reference inside app.services.embedding_hooks, not the global
- [Phase 03-vector-database]: Plan 03-04: BackgroundTasks _embed_and_store coroutine never raises (Pitfall 6) - all failure paths log + mark_failed so retry worker can find them later
- [Phase 03-vector-database]: Plan 03-04: embedding_retry_worker stops BEFORE WS/heartbeat in shutdown so in-flight DB updates land while connection layer is still live
- [Phase 03-vector-database]: Plan 03-05: HTTPException detail must be a string - OpenHub middleware re-wraps exc.detail into ProblemDetail.detail (typed str), so dict-typed details raise ValidationError and turn 400/404/503 into 500. Encode problem code as 'code: message' string instead.
- [Phase 03-vector-database]: Plan 03-05: enable_vector test fixture must patch app.database.vector_availability.is_vector_enabled, NOT routes_search.require_vector - FastAPI captures the Depends callable at router creation and module-level reassignment is too late.
- [Phase 03-vector-database]: Plan 03-05: Per-entity shortcuts use POST /search alongside existing GET /search (LIKE-based). FastAPI dispatches by method so the two coexist - no /vector-search rename needed. clear_embedding never DELETE FROM the entity table - UPDATE-only with embedding_status='deleted'.
- [Phase 03]: Plan 03-06: VEC-06 closeout - openapi_tags entry in FastAPI() constructor + lifespan vector_search_disabled startup warning + README Vector Search (Beta) section + CHANGELOG. Tests must use capsys (not caplog) for structlog PrintLoggerFactory output.
- [Phase 04-command-center-ui]: Plan 04-08: SPA fallback via catch-all FastAPI route + separate /dashboard/assets StaticFiles mount - StaticFiles(html=True) only serves index.html on directory requests, not deep links; catch-all with path-traversal guard is explicit, testable, and correct for any shareable URL under /dashboard
- [Phase 04-command-center-ui]: Plan 04-08: TanStack Router basepath derived from import.meta.env.BASE_URL with trailing-slash strip and '/' fallback - same build artifact works in dev ('/') and prod ('/dashboard') without duplicate configs
- [Phase 04-command-center-ui]: Plan 04-08: Regression guards over permissive assertions - strict deep-link test fails loudly if catch-all is deleted; base-href test fails if vite.config.ts base regresses; favicon test fails if href flips back to absolute
- [Phase 04-command-center-ui]: Plan 04-06: Used existing compositional ResponsiveList (Header/Row/Cell) instead of the plan's proposed generic <T> API to avoid regressing 04-05 and 04-05b routes
- [Phase 04-command-center-ui]: Plan 04-06: Kept /v1/health handler in mocks/handlers/health.ts (plan said empty) because useHealth test + Topbar health dot depend on it - removing breaks Plan 04-04 contract
- [Phase 04-command-center-ui]: Plan 04-06: JsonViewer primitive uses native <details open> for collapse with syntax-aware color tokens (emerald/sky/violet/zinc) - no third-party JSON viewer library added
- [Phase 04-command-center-ui]: Plan 04-09: GET /v1/tasks/{task_id}/trace new endpoint chosen over schema change or WS event - zero schema work, reuses existing trace_events.task_id column, direct inverse of POST /v1/traces/event write path
- [Phase 04-command-center-ui]: Plan 04-09: TraceSpan type hoisted to web/src/types/entities.ts so TraceTimeline and useTaskTrace share one definition; prevents silent drift between hook return shape and component prop shape
- [Phase 04-command-center-ui]: Plan 04-09: animate-pulse div fallback instead of shadcn Skeleton (not installed); matches Skeleton visual without adding a shadcn dep for one loading indicator

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 1 planning will need a code read of app/dependencies.py, routes_auth.py, and app/main.py to confirm full scope of auth stub fix and DDL consolidation before estimating plan count
- Phase 3 planning will need to verify Turso/libSQL vector column API surface against existing AGENTHUB_ZVEC_PATH config key before planning the migration

## Session Continuity

Last session: 2026-04-19T14:08:01.600Z
Stopped at: Completed 04-09-PLAN.md
Resume file: None
