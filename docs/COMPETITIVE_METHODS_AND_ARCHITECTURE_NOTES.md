# Competitive Methods and Architecture Notes

Date: 2026-05-17

Purpose: capture useful patterns from adjacent AI coding-agent coordination projects and translate them into OpenHub product/architecture decisions.

## Reference projects reviewed

Closest practical neighbors:

- CodeKanban (`fy0/CodeKanban`)
- Claude Code Studio (`Lexus2016/claude-code-studio`)
- Claw-Kanban (`GreenSheep01201/Claw-Kanban`)
- AI Agent Board (`DanWahlin/ai-agent-board`)
- KanVibe (`rookedsysc/kanvibe`)
- Automagik Forge (`automagik-dev/forge`)
- Kagan (`kagan-sh/kagan`)
- OpenBotX (`openbotx/openbotx`)
- Relai (`phillipsio/relai`)
- taskboard-mcp (`hazardland/taskboard-mcp`)

Broader framework references:

- AutoGen / AG2
- CrewAI
- LangGraph
- MetaGPT / ChatDev
- OpenHands
- Dify / Flowise / TaskingAI / SuperAGI

## Positioning conclusion

OpenHub should avoid becoming only “a Kanban board for Claude Code.” That space is crowded.

OpenHub should position itself as:

> The coordination backend for AI coding agents: registry, task routing, verification gates, live dashboard, and MCP/API access for humans and agents working across machines.

Short form:

> Not another coding agent. The coordination layer for all of them.

## Methods worth adopting

### 1. Agent state vocabulary beyond online/offline

Borrowed from CodeKanban/KanVibe-style status detection.

OpenHub should expose richer agent state:

- `online`
- `offline`
- `idle`
- `working`
- `blocked`
- `needs_approval`
- `stale`
- `failed`
- `recovering`

Status should be grounded in heartbeat freshness plus recent task/session events, not only a stale `status='online'` row.

### 2. Agent onboarding snippets

Borrowed from Claw-Kanban’s AGENTS.md orchestration rules.

OpenHub should provide copy-paste onboarding blocks for:

- `AGENTS.md`
- `CLAUDE.md`
- `.hermes.md`
- Cursor/Codex/OpenCode equivalent instruction files
- MCP client setup

The goal is that an agent can learn how to:

- register or join via invite
- claim tasks
- emit heartbeat/status
- post evidence
- mark blocked/needs_review
- avoid printing secrets

### 3. Provider/adapter abstraction

Borrowed from AI Agent Board and general multi-agent orchestrators.

Define a stable adapter model:

```text
AgentProvider
AgentSession
AgentEvent
AgentCapability
AgentCredential
AgentRuntime
```

Each integration should normalize events into a common event stream:

```text
session.started
command.started
command.finished
file.changed
task.blocked
approval.requested
evidence.submitted
task.completed_claimed
task.verified
```

### 4. Verification-first lifecycle

This is OpenHub’s strongest differentiator.

Task state should distinguish claimed completion from verified completion:

```text
queued
claimed
running
completed_claimed
verification_running
verified
needs_review
failed
blocked
stale
```

A task should not close just because an agent says “done.” Require evidence:

- tests run and result
- diff / changed files
- logs
- PR / branch reference
- artifact links
- reviewer/judge outcome

### 5. Structural human review gate

Borrowed from Kagan/Forge style positioning.

OpenHub should explicitly support:

- auto verification for low-risk tasks
- human review for risky changes
- policy-based routing: security/auth/db/deploy tasks require review
- “merge allowed” only after verification/review passes

Core claim:

> Humans stay in control; agents produce verifiable work.

### 6. Live task detail page

Borrowed from KanVibe, Claude Code Studio, AI Agent Board.

Each task should have a live detail page showing:

- current agent/session
- logs/events timeline
- commands run
- files changed
- branch/worktree
- PR link
- artifacts
- evidence bundle
- verification status
- approval prompts

### 7. Cross-machine invite/join model

Borrowed from Relai and aligned with OpenHub ACN.

OpenHub should keep project/node/agent identity explicit:

- short-lived invite code (`inv_...`)
- per-agent permanent key (`oh_...`)
- admin key (`ak_...`) never leaves server/admin context
- per-agent tokens scoped to project/node where possible
- project boundary as trust boundary

### 8. MCP-first access

Borrowed from Relai/taskboard-mcp/Kagan.

OpenHub should expose task board, registry, messages, and evidence via MCP so Claude Code, Cursor, Codex, Hermes, OpenCode, and other clients can use the same state without bespoke integrations.

Candidate MCP resources/tools:

- list/read/create/update tasks
- claim/release task
- submit evidence
- read agent registry
- send/read coordination messages
- search semantic memory
- subscribe/read event stream snapshot

### 9. CLI-first plus dashboard

Borrowed from Relai/Kagan.

Dashboard is valuable, but core capabilities should exist first as:

- REST API
- CLI commands
- MCP tools
- WebSocket/SSE events

The dashboard should be a view/control surface over the same primitives, not the only product path.

### 10. Worktree/session isolation

Borrowed from CodeKanban, AI Agent Board, KanVibe.

For coding tasks, support explicit isolation metadata:

- repo path
- base branch
- task branch
- worktree path
- assigned agent
- session id
- PR id/url

This reduces conflicts and makes parallel work safer.

## Language / microservice architecture guidance

OpenHub should stay coherent at the core, but allow function-specific language choices where the job clearly benefits.

Principle:

> Python/FastAPI remains the control plane. Other languages are specialized workers or edge services, not random rewrites.

### Recommended split by function

#### Python: control plane and AI integration

Use Python for:

- FastAPI API server
- auth/session logic
- ACN registry
- task routing and verification orchestration
- LLM/provider adapters
- embedding/vector hooks
- admin scripts
- CLI integration where Python ecosystem helps

Why: current stack, FastAPI, Pydantic, AI/LLM libraries, rapid iteration.

#### TypeScript: dashboard and agent-facing web UX

Use TypeScript for:

- React/Vite dashboard
- live task detail UI
- frontend API client/types
- browser-side MCP/setup helpers if needed

Why: best fit for UI, typed frontend contracts, ecosystem.

#### Go: small durable local binaries and bridge daemons

Consider Go for:

- lightweight cross-platform bridge daemon
- file watcher / process supervisor
- terminal/session monitor
- single-binary local agent connector
- high-reliability heartbeat sidecar

Why: static binaries, low memory, easy install, good concurrency.

#### Rust: safety-critical or high-performance local runtime pieces

Consider Rust only when justified for:

- sandbox boundary helper
- high-throughput event/log collector
- secure local credential helper
- file-diff/indexing engine
- terminal PTY multiplexer if safety/performance matters

Why: memory safety and performance. Avoid Rust for ordinary business logic unless complexity is clearly worth it.

#### Node.js/TypeScript backend workers: CLI ecosystem adapters

Consider Node for:

- integrations where target toolchain is Node-first
- Claude/Codex/OpenCode wrapper experiments if SDKs are JS-first
- VSCode/Cursor extension companion services

Why: extension/tooling ecosystem. Keep it behind a stable OpenHub API.

#### SQLite/Turso/libSQL: state substrate

Use as authoritative state layer for:

- registry
- tasks
- events
- heartbeats
- evidence metadata
- audit log

Avoid per-service hidden databases unless the boundary is explicit and synchronized through events.

### Boundary rule

Introduce a new service/language only if it has a crisp boundary:

- stable API or message contract
- clear owner/function
- independent test suite
- health endpoint
- versioned event schema if asynchronous
- no direct secret leakage through logs

Bad split:

```text
Some task code in Python, some in Go, same tables, unclear ownership.
```

Good split:

```text
Python API owns tasks.
Go bridge daemon reports process/session events through /v1/events or WebSocket/MCP.
TypeScript dashboard consumes the same events.
```

## Practical architecture target

```text
OpenHub Core API                Python/FastAPI
Dashboard                       TypeScript/React
Agent Bridge                    Python first, Go later if packaging/reliability demands it
Local Process/Terminal Monitor  Go candidate
Verification Workers            Python first; language-specific plugins optional
MCP Server                      Python first, because it sits near core state
Event Stream                    Python API + WebSocket/SSE; typed event schema shared with frontend
Sandbox/PTY Advanced Runtime    Rust only if needed
```

## Product principles to preserve

1. Do not compete as “another coding agent.”
2. Coordinate all agents.
3. Make work durable beyond the chat window.
4. Verify outputs before closing tasks.
5. Keep humans in control with review gates.
6. Prefer API/CLI/MCP primitives; dashboard is a first-class client, not the only interface.
7. Use microservices only where they reduce operational risk or improve install/runtime quality.
8. Keep the control plane simple, typed, observable, and testable.
