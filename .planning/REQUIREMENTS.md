# Requirements: OpenHub v1.0

**Defined:** 2026-04-07
**Core Value:** Any developer can self-host OpenHub, connect their AI agents, and coordinate multi-agent workflows from a single command center - reliably and without conflicts.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Backend Hardening

- [ ] **HARD-01**: Auth stub in app/dependencies.py removed - all routes use real JWT/API key auth from app/auth/
- [ ] **HARD-02**: Hardcoded admin credentials (admin/admin123) replaced with env-configurable or first-run setup
- [ ] **HARD-03**: Capabilities stored as proper JSON (not Python str()) so json.loads() works for task matching
- [ ] **HARD-04**: Heartbeat monitor wired into app lifespan and actually runs to detect offline agents
- [x] **HARD-05**: CORS defaults locked down (no wildcard in production)
- [x] **HARD-06**: Schema DDL consolidated from inline main.py into versioned migration files
- [x] **HARD-07**: OpenAPI /docs endpoint enabled and accessible
- [x] **HARD-08**: Structured error responses with consistent error format across all endpoints
- [x] **HARD-09**: datetime.utcnow() calls unified to timezone-aware datetime handling
- [x] **HARD-10**: Duplicate auth helper modules consolidated into single source of truth

### WebSocket Real-time

- [x] **WS-01**: /v1/ws/ui endpoint for dashboard clients with JWT authentication via initial-message frame
- [ ] **WS-02**: ConnectionManager class replacing module-level _connections dict with proper connect/disconnect cleanup
- [ ] **WS-03**: broadcast_to_ui() helper for pushing events to all connected dashboard clients
- [ ] **WS-04**: Agent status change events (online/offline/idle) broadcast to UI clients in real-time
- [ ] **WS-05**: Task lifecycle events (created/claimed/running/completed/failed) broadcast to UI clients
- [x] **WS-06**: Workflow step progress events broadcast to UI clients

### Test Suite

- [x] **TEST-01**: Unit tests for auth system (JWT creation/validation, API key verification, RBAC enforcement)
- [x] **TEST-02**: Unit tests for capability matching (exact match, fuzzy match, scoring)
- [x] **TEST-03**: Integration tests for task lifecycle (create, claim, start, complete, fail, retry)
- [x] **TEST-04**: Integration tests for agent registration and heartbeat/offline detection
- [x] **TEST-05**: Integration tests for WebSocket connections (auth, event broadcast, disconnect cleanup)
- [ ] **TEST-06**: E2E tests with Playwright for critical UI flows (login, agent list, task create/cancel)

### Command Center UI

- [ ] **UI-01**: JWT login form with token management (stored in memory, not localStorage)
- [ ] **UI-02**: Live agent status board showing online/offline/idle states with last-seen timestamps (WebSocket-driven)
- [ ] **UI-03**: Task list with filterable status columns and real-time updates via WebSocket
- [ ] **UI-04**: Task create form allowing dispatch from the UI with agent selection
- [ ] **UI-05**: Task cancel action on running tasks from the UI
- [ ] **UI-06**: Workflow step-list view with read-only status badges per step
- [ ] **UI-07**: Agent detail drilldown showing capabilities, current task, heartbeat history
- [ ] **UI-08**: Health/connectivity indicator using /v1/health in the top bar
- [ ] **UI-09**: Structured error display via toast notifications for failed operations
- [ ] **UI-10**: DLQ (Dead Letter Queue) panel showing failed tasks with manual retry button
- [ ] **UI-11**: Cost tracking display showing per-agent spend and per-task cost
- [ ] **UI-12**: Distributed trace viewer in task detail showing tool calls, sub-steps, timing
- [ ] **UI-13**: Shared memory key/value viewer with size and age metadata
- [ ] **UI-14**: Resource lock panel showing active locks and lock conflicts as warnings
- [ ] **UI-15**: Mobile-responsive layout using Tailwind breakpoints (table-to-card at small screens)
- [ ] **UI-16**: WebSocket hook with exponential backoff reconnection and "reconnecting..." banner

### Vector Database

- [x] **VEC-01**: Turso/libSQL native vector columns (F32_BLOB) for semantic search - replacing zvec
- [x] **VEC-02**: Vector similarity search using vector_distance_cos for context/memory queries
- [x] **VEC-03**: DiskANN vector indexing for performant approximate nearest neighbor search
- [x] **VEC-04**: Auto-indexing hooks on memory, task, and artifact write paths to generate embeddings
- [ ] **VEC-05**: Vector search API endpoints (search, index, delete) in app/api/
- [x] **VEC-06**: Feature flagged as opt-in beta with documented experimental status

### Open Source Readiness

- [ ] **OSS-01**: README with 5-minute quickstart covering both Docker and pip install paths
- [x] **OSS-02**: API documentation via exposed OpenAPI /docs with endpoint descriptions
- [ ] **OSS-03**: License file (MIT or Apache 2.0) clearly stated in repo root
- [ ] **OSS-04**: Contributing guide with development setup, code style, and PR process
- [ ] **OSS-05**: pip install path (pip install openhub && openhub start) as alternative to Docker
- [ ] **OSS-06**: Docker Compose hardened for production (health checks, restart policies, volume mounts)

### Deployment & Production

- [x] **PROD-01**: slowapi rate limiting wired into middleware for API protection
- [x] **PROD-02**: prometheus-client metrics endpoint for monitoring
- [ ] **PROD-03**: Graceful shutdown handling for in-flight tasks and WebSocket connections
- [x] **PROD-04**: Production logging configuration with structured JSON output

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Native Mobile

- **MOB-01**: React Native/Expo mobile app for iOS and Android
- **MOB-02**: Push notifications for agent status changes and task completions

### Advanced Features

- **ADV-01**: OAuth/SSO integration (GitHub, Google login)
- **ADV-02**: Multi-tenancy with team/org support
- **ADV-03**: Visual workflow builder (drag-drop DAG editor)
- **ADV-04**: Real Hatchet integration replacing simulated workflows
- **ADV-05**: Redis Pub/Sub for multi-worker WebSocket broadcasting
- **ADV-06**: Plugin/extension marketplace

## Out of Scope

| Feature | Reason |
|---------|--------|
| Visual workflow builder | 3-4x complexity of step-list view; not OpenHub's core advantage |
| Prompt editing / LLM config in UI | Agents manage their own LLM config; hub coordinates tasks, not prompts |
| Multi-tenancy | Single-instance deployment for v1.0; explicit constraint |
| OAuth/SSO | JWT + API keys sufficient for self-hosted use case |
| Agent code execution sandbox | Hub coordinates, never executes agent code |
| Real-time log streaming | Solved by Grafana/Loki; not OpenHub's job |
| Hosted/SaaS offering | Open source self-host only for v1.0 |
| AI-powered anomaly detection | Surface raw metrics; users wire own alerting |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| HARD-01 | Phase 1 | Pending |
| HARD-02 | Phase 1 | Pending |
| HARD-03 | Phase 1 | Pending |
| HARD-04 | Phase 1 | Pending |
| HARD-05 | Phase 1 | Complete |
| HARD-06 | Phase 1 | Complete |
| HARD-07 | Phase 1 | Complete |
| HARD-08 | Phase 1 | Complete |
| HARD-09 | Phase 1 | Complete |
| HARD-10 | Phase 1 | Complete |
| OSS-02 | Phase 1 | Complete |
| PROD-01 | Phase 1 | Complete |
| PROD-02 | Phase 1 | Complete |
| PROD-04 | Phase 1 | Complete |
| WS-01 | Phase 2 | Complete |
| WS-02 | Phase 2 | Pending |
| WS-03 | Phase 2 | Pending |
| WS-04 | Phase 2 | Pending |
| WS-05 | Phase 2 | Pending |
| WS-06 | Phase 2 | Complete |
| TEST-01 | Phase 2 | Complete |
| TEST-02 | Phase 2 | Complete |
| TEST-03 | Phase 2 | Complete |
| TEST-04 | Phase 2 | Complete |
| TEST-05 | Phase 2 | Complete |
| VEC-01 | Phase 3 | Complete |
| VEC-02 | Phase 3 | Complete |
| VEC-03 | Phase 3 | Complete |
| VEC-04 | Phase 3 | Complete |
| VEC-05 | Phase 3 | Pending |
| VEC-06 | Phase 3 | Complete |
| UI-01 | Phase 4 | Pending |
| UI-02 | Phase 4 | Pending |
| UI-03 | Phase 4 | Pending |
| UI-04 | Phase 4 | Pending |
| UI-05 | Phase 4 | Pending |
| UI-06 | Phase 4 | Pending |
| UI-07 | Phase 4 | Pending |
| UI-08 | Phase 4 | Pending |
| UI-09 | Phase 4 | Pending |
| UI-10 | Phase 4 | Pending |
| UI-11 | Phase 4 | Pending |
| UI-12 | Phase 4 | Pending |
| UI-13 | Phase 4 | Pending |
| UI-14 | Phase 4 | Pending |
| UI-15 | Phase 4 | Pending |
| UI-16 | Phase 4 | Pending |
| OSS-01 | Phase 5 | Pending |
| OSS-03 | Phase 5 | Pending |
| OSS-04 | Phase 5 | Pending |
| OSS-05 | Phase 5 | Pending |
| OSS-06 | Phase 5 | Pending |
| PROD-03 | Phase 5 | Pending |
| TEST-06 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 54 total
- Mapped to phases: 54
- Unmapped: 0

---
*Requirements defined: 2026-04-07*
*Last updated: 2026-04-07 after roadmap creation*
