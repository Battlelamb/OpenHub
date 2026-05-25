---
last_mapped_commit: 13fcce7400bd66c4e9b5412c9ed677cd215f019a
---
# Codebase Concerns

**Analysis Date:** 2026-05-25

## Tech Debt

**Large route modules mix transport and business logic:**
- Issue: `app/api/routes_acn.py` (~1261 lines) and `app/api/routes_tasks.py` (~848 lines) contain substantial orchestration and persistence logic directly in route modules.
- Files: `app/api/routes_acn.py`, `app/api/routes_tasks.py`, `app/api/routes_agents.py`.
- Impact: Harder to test isolated invariants; new changes risk route-level duplication instead of service-level reuse.
- Fix approach: Extract stable service/repository functions in small GSD slices, preserving route contracts with regression tests.

**Health route contains placeholder counts:**
- Issue: TODO markers in `app/api/routes_health.py` still report placeholder agent/task counts and DB/Redis checks.
- Files: `app/api/routes_health.py`.
- Impact: Dashboard/operator truth can diverge from real ACN/task state.
- Fix approach: Keep `/v1/health` as process health or wire truthful counts through runtime DB/service calls; use `/v1/acn/status` and `/v1/tasks/search` for product truth.

**Two workflow route surfaces share `/v1/workflows`:**
- Issue: Both `app/api/routes_workflows.py` and `app/api/routes_workflow.py` mount `/v1/workflows`-prefixed routers with different semantics.
- Files: `app/api/routes_workflows.py`, `app/api/routes_workflow.py`, `app/main.py`.
- Impact: Route ordering and naming confusion can make dashboard hooks or docs hit the wrong conceptual workflow API.
- Fix approach: Document the split clearly or consolidate/rename one surface with compatibility redirects and tests.

**Raw SQL schema evolution is spread across migrations and runtime expectations:**
- Issue: Repositories and services assume table/column shapes while migrations live in `alembic/` and helper code.
- Files: `app/database/repositories/*.py`, `app/database/migrations.py`, `alembic/versions/*.py`.
- Impact: Turso/local SQLite drift can surface as runtime failures after deploy.
- Fix approach: Add schema-contract tests for critical tables and run migrations in packaging/deploy smoke.

## Known Bugs

**Potential misleading health dashboard state:**
- Symptoms: Health endpoint can be `healthy` while ACN agents/tasks are absent/stale or placeholder counts remain zero.
- Files: `app/api/routes_health.py`, dashboard health views under `web/src/routes/_authed/health.tsx`.
- Trigger: Operators rely on aggregate `/v1/health` instead of domain status endpoints.
- Workaround: Verify ACN via `/v1/acn/status` and task truth via `/v1/tasks/search` until health truth is fully wired.

**Dashboard availability depends on build artifact placement:**
- Symptoms: `/dashboard` is not mounted even though the API container is healthy.
- Files: `app/main.py`, `web/vite.config.ts`, `Dockerfile`.
- Trigger: `web/dist/index.html` missing beside the backend at runtime.
- Workaround: Run `cd web && npm run build`; package/copy dashboard assets for deployment before claiming dashboard is live.

## Security Considerations

**Secret handling in generated docs and diagnostics:**
- Risk: GSD maps/evidence are committed, so reading `.env` or key files would create a credential leak.
- Files: `.planning/codebase/*.md`, `.env.example`, `app/config.py`.
- Current mitigation: Mapper forbids reading `.env`, key, credential, and token files; this map only uses env var names from safe config/docs.
- Recommendations: Run a changed-file secret scan before every commit; preserve known-good env files without printing values.

**Admin-key vs dashboard-JWT boundary:**
- Risk: ACN admin keys could leak to browser code if dashboard features call admin-key endpoints directly.
- Files: `app/api/routes_acn.py`, `app/api/routes_p2.py`, `web/src/lib/api-client.ts`.
- Current mitigation: Dashboard invite path uses `/v1/acn/dashboard/invite` with admin JWT; DLQ routes accept JWT admin or server-side admin key path.
- Recommendations: Keep permanent `ak_...` values server-side and add route tests for every dashboard admin wrapper.

**CORS and required credential defaults:**
- Risk: Unsafe defaults or wildcard CORS in production weaken deployment posture.
- Files: `app/config.py`, `tests/conftest.py`, `.env.example`.
- Current mitigation: required admin/JWT fields have no production defaults; tests set safe dummy values before app import.
- Recommendations: Keep production examples explicit; avoid wildcard CORS outside tests/local dev.

## Performance Bottlenecks

**Synchronous DB calls inside async routes:**
- Problem: Routes are async, but `Database` methods are synchronous sqlite/libSQL calls.
- Files: `app/database/connection.py`, `app/api/routes_*.py`.
- Cause: Custom DB wrapper uses blocking `sqlite3`/libSQL calls directly.
- Improvement path: Keep operations short; move heavy loops to background jobs/workers; consider async DB adapter only as a deliberate architectural phase.

**Large route files increase import/startup cost and review cost:**
- Problem: Very large modules slow navigation and make targeted reviews expensive.
- Files: `app/api/routes_acn.py`, `app/api/routes_tasks.py`, `app/services/task_service.py`.
- Cause: Feature growth without service/module splitting.
- Improvement path: Extract service helpers behind tests in small slices, not broad rewrites.

**Embedding/vector search can be heavy:**
- Problem: Local sentence-transformers backend is heavy and vector search requires Turso availability.
- Files: `app/services/embedding_service.py`, `app/services/embedding_retry_worker.py`, `app/api/routes_search.py`.
- Cause: ML model load and remote vector DB latency.
- Improvement path: Keep vector search opt-in, expose unavailable state clearly, and use retry worker/backoff for indexing.

## Fragile Areas

**ACN heartbeat truth:**
- Files: `app/api/routes_acn.py`, `app/database/repositories/acn_nodes.py`, `app/database/repositories/remote_agent_mappings.py`, `tests/unit/test_acn_node_heartbeat.py`.
- Why fragile: Node heartbeat and agent heartbeat are easy to conflate; false-online agents are a known class of bug.
- Safe modification: Preserve tests that prove node heartbeat updates node liveness only and mapped agent heartbeat requires agent identity/API key metadata.
- Test coverage: Existing ACN tests cover core regressions; add route-level tests when changing heartbeat/status payloads.

**Task status transitions / Kanban drag-drop:**
- Files: `app/api/routes_tasks.py`, `app/services/task_service.py`, `web/src/components/kanban/KanbanBoard.tsx`, `web/src/hooks/queries/useTasks.ts`.
- Why fragile: UI drag/drop, backend transition rules, timestamps, owner reset, and conflict responses must stay aligned.
- Safe modification: Add backend transition tests and frontend mutation/refetch tests before UX changes.
- Test coverage: `tests/integration/test_patch_task_status_endpoint.py`, `web/src/components/kanban/KanbanBoard.test.tsx`.

**Dashboard auth/session redirect behavior:**
- Files: `app/auth/dependencies.py`, `app/auth/jwt_auth.py`, `app/api/routes_auth.py`, `web/src/components/forms/LoginForm.tsx`, `web/src/lib/api-client.ts`.
- Why fragile: Synthetic admin JWTs intentionally do not map to normal agent rows.
- Safe modification: Keep route hooks at top level in React; backend admin subjects should pass admin route dependencies without agents-table lookup.
- Test coverage: `tests/unit/test_admin_dashboard_auth.py`, `tests/unit/test_dashboard_auth_alignment.py`, `web/src/components/forms/LoginForm.test.tsx`.

**WebSocket dashboard sync:**
- Files: `app/services/connection_manager.py`, `app/api/routes_ws_ui.py`, `web/src/hooks/useWebSocketSync.ts`.
- Why fragile: Event names, payload fields, and query keys must match.
- Safe modification: Reuse existing event union in `useWebSocketSync.ts`; add backend broadcast tests and frontend event handling tests.
- Test coverage: `tests/unit/test_acn_ws_events.py`, `tests/unit/test_connection_manager.py`, `web/src/hooks/useWebSocketSync.test.ts`.

## Scaling Limits

**SQLite default state store:**
- Current capacity: Suitable for local/self-hosted small deployments.
- Limit: Concurrent high-volume agent/task writes can hit SQLite locking/contention.
- Scaling path: Turso/libSQL mode for remote/state scaling; keep write paths short and indexes/migrations explicit.

**In-process background workers:**
- Current capacity: One API process manages heartbeat and embedding retry worker from lifespan.
- Limit: Multi-process deployments can duplicate workers unless guarded.
- Scaling path: Add leader election or external worker process before horizontal scaling.

**WebSocket fanout:**
- Current capacity: `ConnectionManager` tracks UI connections in process memory.
- Limit: Multiple API processes need cross-process pub/sub for consistent live UI updates.
- Scaling path: Redis/pubsub event bus or single writer process.

## Dependencies at Risk

**Vector stack dimensions/provider coupling:**
- Risk: Switching local/OpenAI-compatible embedding providers can mismatch vector dimensions.
- Impact: Search quality or writes fail if dimensions do not match migration column width.
- Migration plan: Use `AGENTHUB_EMBEDDING_DIM_OVERRIDE` only with schema alignment and regression tests.

**Dual Python dependency declarations:**
- Risk: `requirements.txt` and `pyproject.toml` can drift.
- Impact: pip install package and dev/runtime environment differ.
- Migration plan: Periodically compare pinned requirements with package metadata or derive one from the other in release automation.

**Frontend route generation:**
- Risk: `web/src/routeTree.gen.ts` is generated from TanStack Router plugin and can drift if route files change without build/typecheck.
- Impact: Navigation/type errors surface late.
- Migration plan: Run `cd web && npm run typecheck` after route changes.

## Missing Critical Features

**Durable supervisor packaging for local services:**
- Problem: Repository supports CLI/Docker, but long-lived deployment health depends on external supervisor/systemd setup.
- Blocks: Reliable always-on API/bridge operation without manual process management.

**CI workflow absence:**
- Problem: No `.github/workflows` files detected during mapping.
- Blocks: Automatic PR gating for backend/frontend/E2E checks.

**Dashboard packaging in Docker image:**
- Problem: Dockerfile copies backend only; `/dashboard` mount depends on `web/dist` being present beside app.
- Blocks: Claiming complete dashboard deployment from API image alone.

## Test Coverage Gaps

**Health truth counts:**
- What's not tested: Real DB-backed counts/status in `/v1/health` if it is expected to show product truth.
- Files: `app/api/routes_health.py`.
- Risk: Operators see green/zero while ACN/task state is elsewhere.
- Priority: Medium.

**Packaging with built dashboard assets:**
- What's not tested: Docker or wheel includes/serves `web/dist` in production shape.
- Files: `Dockerfile`, `pyproject.toml`, `app/main.py`, `web/dist` build output.
- Risk: API deploys successfully without dashboard UI.
- Priority: High when release packaging is active.

**Workflow API split:**
- What's not tested: No ambiguity between `routes_workflow.py` and `routes_workflows.py` for all dashboard/backend callers.
- Files: `app/api/routes_workflow.py`, `app/api/routes_workflows.py`, `web/src/hooks/queries/useWorkflows.ts`.
- Risk: wrong endpoint contract or stale in-memory state.
- Priority: Medium.

---

*Concerns audit: 2026-05-25*
