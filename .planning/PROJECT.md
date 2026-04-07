# OpenHub v1.0 - Production Ready

## What This Is

OpenHub is a multi-agent coordination platform that enables multiple AI agents (Claude Code, Cursor, Copilot, etc.) to work together on the same codebase without conflicts. It provides agent registration, task management, workflow orchestration, and real-time coordination through a centralized hub. v1.0 targets open source release with a command center UI, production-grade backend, and responsive mobile web support.

## Core Value

Any developer can self-host OpenHub, connect their AI agents, and coordinate multi-agent workflows from a single command center - reliably and without conflicts.

## Requirements

### Validated

- Agent registration, heartbeat, and capability matching - existing
- Task lifecycle management (create, claim, start, complete, fail, retry) - existing
- JWT + API key authentication with Casbin RBAC - existing
- Hatchet workflow orchestration integration - existing
- Agent-workflow coordination (smart assignment, planning, monitoring) - existing
- SQLite database with WAL mode and migration system - existing
- Docker deployment support - existing
- MCP tool sharing, agent templates, rate limiting, dead letter queue - existing
- Shared memory/context store - existing
- Workflow engine (create, run, advance, multi-step DAG) - existing
- Artifacts, resource locks, tracing, cost tracking - existing

### Active

- [ ] Command center UI (React + Vite) with live dashboard and agent/task/workflow control
- [ ] WebSocket real-time communication for live updates
- [ ] Vector database integration for semantic search and context
- [ ] Comprehensive test suite (unit, integration, e2e)
- [ ] Production error handling and graceful failure recovery
- [ ] Structured logging improvements and observability
- [ ] Responsive web design for mobile access
- [ ] Production deployment hardening (Docker + pip install)
- [ ] Open source documentation (README, setup guides, contribution guide, API docs)

### Out of Scope

- Native mobile app (React Native/Expo) - deferred to v2, responsive web first
- OAuth/SSO integration - JWT + API keys sufficient for v1.0
- Multi-tenancy - single-instance deployment for v1.0
- Paid/hosted offering - open source self-host only

## Context

- **Live deployment** exists at hub.brunhilde.cloud with 4 agents (OpenClaw, Qwen, Codex, Claude)
- **Backend is mature**: layered architecture (routes -> services -> repositories -> database), well-structured with clear separation of concerns
- **Zero tests exist** despite pytest being in dependencies - this is the biggest stability gap
- **No frontend exists** - the command center UI is entirely new
- **Target audience**: open source developers who want to coordinate multiple AI agents
- **Existing codebase**: ~1,463 lines of architecture documentation in .planning/codebase/

## Constraints

- **Backend stack**: Python 3.11+ / FastAPI / SQLite (already established, not changing)
- **Frontend stack**: React + Vite (chosen for lightweight SPA dashboard)
- **Deployment**: Must support both Docker and pip install for open source accessibility
- **Compatibility**: Must maintain existing API contracts - agents already running in production

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| React + Vite over Next.js for frontend | Lighter weight, pure SPA fits dashboard use case, no SSR needed | - Pending |
| Responsive web over native mobile for v1.0 | Lower complexity, single codebase, native deferred to v2 | - Pending |
| Open source target | Broader impact, community-driven development | - Pending |
| Solidify existing before adding features | Production reliability more important than feature count | - Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? - Move to Out of Scope with reason
2. Requirements validated? - Move to Validated with phase reference
3. New requirements emerged? - Add to Active
4. Decisions to log? - Add to Key Decisions
5. "What This Is" still accurate? - Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check - still the right priority?
3. Audit Out of Scope - reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-07 after initialization*
