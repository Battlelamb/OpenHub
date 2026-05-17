# ADR: Function-Specific Language Boundaries

Date: 2026-05-17

Status: Accepted

## Context

OpenHub is evolving from a multi-agent task hub into the coordination backend for AI coding agents. Adjacent tools show that dashboards and task boards are easy to copy, while durable coordination requires a stronger control plane: registry, task routing, verification gates, evidence, events, MCP/API access, and truthful runtime state.

During planning, we considered whether OpenHub should diversify languages and services in a microservice style. A full rewrite or broad polyglot split would increase operational complexity before the product boundary is stable.

## Decision

OpenHub will use a **function-specific language strategy** rather than a full rewrite or broad microservice split.

Python/FastAPI remains the authoritative control plane:

- REST API
- auth/session
- ACN registry
- task routing
- task state/lifecycle
- evidence and verification orchestration
- MCP/API coordination surface
- LLM/provider adapters
- embedding/vector hooks
- persistence ownership through SQLite/Turso/libSQL

TypeScript/React remains the dashboard and human-facing live UX layer:

- dashboard routes
- task/agent detail pages
- live event display
- typed frontend contracts
- admin controls

Go is a candidate only for narrow local runtime/edge services when packaging or reliability demands it:

- cross-platform bridge daemon
- local process/session monitor
- heartbeat sidecar
- file watcher
- single-binary connector

Rust is reserved for safety-critical or high-performance runtime boundaries:

- sandbox helpers
- secure credential helper
- PTY/log collector
- diff/indexing engine
- other memory-safety/performance-critical components

Node.js/TypeScript backend workers are allowed only where the integration ecosystem is JS-first:

- VSCode/Cursor companion services
- browser/devtool adapters
- JS-first MCP/extension wrappers

## Boundary Rule

Core task, agent, event, verification, and registry state is owned by the Python API and the authoritative database layer.

Specialized services may report events, heartbeats, evidence, or runtime observations through stable API/MCP/WebSocket contracts, but they must not become hidden second owners of core state.

Bad split:

```text
Python updates some task fields.
Go updates other task fields directly in the same database.
Node decides completion state in parallel.
```

Good split:

```text
Python API owns task state and verification.
Go bridge daemon reports process/session/heartbeat/evidence events to the API.
TypeScript dashboard consumes API/WebSocket state.
Rust sandbox helper returns bounded execution results to the bridge/API.
```

## Required Gate Before Adding a New Service or Language

A new language/service requires all of the following:

1. Crisp ownership boundary.
2. Stable request/event contract.
3. Health check.
4. Independent tests.
5. Secret-safe logging.
6. No direct ownership of core task/agent state unless it is the Python control plane.
7. Operational reason stronger than preference or novelty.
8. Rollback path.

## Consequences

### Positive

- Keeps OpenHub simple enough to ship quickly.
- Prevents premature rewrite pressure.
- Preserves Python’s AI/LLM velocity.
- Allows Go/Rust where they genuinely improve runtime/install/security.
- Keeps the dashboard and API aligned around one source of truth.

### Negative

- Some performance-sensitive work may initially remain in Python longer.
- Future Go/Rust components need explicit contracts before coding starts.
- More discipline is required to avoid “just one direct DB write” shortcuts.

## Current Practical Target

```text
OpenHub Core API                Python/FastAPI
Dashboard                       TypeScript/React
Agent Bridge                    Python first, Go later if packaging/reliability demands it
Local Process/Terminal Monitor  Go candidate
Verification Workers            Python first; language-specific plugins optional
MCP Server                      Python first, near core state
Event Stream                    Python API + WebSocket/SSE
Sandbox/PTY Advanced Runtime    Rust only if needed
```

## References

- `docs/COMPETITIVE_METHODS_AND_ARCHITECTURE_NOTES.md`
- `docs/plans/2026-05-17-openhub-coordination-backend-plan.md`
- `docs/ROADMAP_V2.md`
