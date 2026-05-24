# Phase 07-01 Dashboard Truth Audit

**Date:** 2026-05-24T20:18Z  
**Scope:** Agents, Tasks/Kanban, Workflows, Health dashboard truth sources.  
**Live URL:** `https://hub.brunhilde.cloud`  
**Repo HEAD at audit:** `9a11824`

## Executive summary

- Agents page is now correctly ACN-first and matches live ACN truth.
- Tasks/Kanban page is backend-wired and matches `/v1/tasks/search`.
- Workflow list matches `/v1/workflows/` and currently truthfully shows empty state.
- Health page is the main truth problem: it renders raw `/v1/health`, whose legacy `agents.connected = 0` and task counters do not reflect ACN/task-search reality.
- Live data hygiene issue: production/live DB contains old Playwright/E2E task artifacts, which are true data but visually confusing.

## Route and endpoint inventory

### Agents

- UI route: `/dashboard/agents`
- Component: `web/src/routes/_authed/agents/index.tsx`
- Hook: `web/src/hooks/queries/useAgents.ts`
- Primary endpoint: `/v1/acn/status`
- Fallback endpoint: `/v1/agents/discover/available`
- Detail route: `/dashboard/agents/$agentId`
- Detail hook endpoint: `/v1/agents/${id}`

### Tasks / Kanban

- UI route: `/dashboard/tasks`
- Component: `web/src/routes/_authed/tasks/index.tsx`
- Board: `web/src/components/kanban/KanbanBoard.tsx`
- Hook: `web/src/hooks/queries/useTasks.ts`
- List endpoint: `/v1/tasks/search?page=1&limit=100`
- Detail endpoint: `/v1/tasks/${id}`
- Create endpoint: `POST /v1/tasks/`
- Cancel endpoint: `POST /v1/tasks/${taskId}/cancel`
- Kanban transition endpoint: `PATCH /v1/tasks/${taskId}/status`

### Workflows

- UI route: `/dashboard/workflows`
- Component: `web/src/routes/_authed/workflows/index.tsx`
- Hook: `web/src/hooks/queries/useWorkflows.ts`
- List endpoint: `/v1/workflows/`
- Detail endpoint: `/v1/workflows/${id}`

### Health

- UI route: `/dashboard/health`
- Component: `web/src/routes/_authed/health.tsx`
- Hook: `web/src/hooks/queries/useHealth.ts`
- Endpoint: `/v1/health`

## Live API evidence

### Local and public parity

- Local `/v1/health/simple`: 200 OK
- Public `/v1/health/simple`: 200 OK
- Local `/v1/acn/status`: 200 OK
- Public `/v1/acn/status`: 200 OK

### Public endpoint observations

- `/v1/health`: `status=healthy`, `agents.connected=0`, `tasks.active=0`, `tasks.queued=0`
- `/v1/acn/status`: `nodes=1`, `total_agents=1`, agent `brunhilde`
- `/v1/acn/health`: `total_nodes=1`, `online_nodes=1`, `total_remote_agents=1`
- `/v1/agents/discover/available`: `available_count=0`, `agents=0`
- `/v1/tasks/search?page=1&limit=100`: `total=11`, statuses `completed`, `queued`
- `/v1/workflows/`: `0` workflows

## Browser evidence

Authenticated Playwright smoke against public dashboard showed:

### `/dashboard/agents`

- Shows `1 registered`
- Shows `brunhilde online`
- Shows fresh agent and node heartbeat
- Recent resources include `/v1/acn/status`
- Console issue count: `0`

**Verdict:** Correct. ACN is the source of truth and the visible page matches it.

### `/dashboard/tasks`

- Shows `11 total`
- Shows Kanban columns and task cards
- Recent resources include `/v1/tasks/search?page=1&limit=100`
- Console issue count: `0`

**Verdict:** Correct source of truth. Data hygiene concern: several visible cards are old E2E artifacts.

### `/dashboard/workflows`

- Shows `No workflows running`
- Recent resources include `/v1/workflows/`
- API also returns empty list
- Console issue count: `0`

**Verdict:** Correct.

### `/dashboard/health`

- Shows raw `/v1/health` JSON
- JSON says `agents.connected: 0`
- JSON says task counters `active: 0`, `queued: 0`
- This conflicts with ACN showing `1` online agent and task search showing `11` tasks.

**Verdict:** Misleading. Needs Phase 07-02 fix.

## Findings

### F-01 — Health page shows legacy counters as if they were complete dashboard truth

- **Severity:** Medium
- **Category:** Product truth / UX
- **Route:** `/dashboard/health`
- **Endpoint:** `/v1/health`
- **Observed:** Health JSON reports `agents.connected=0` and task counters `0` while ACN reports 1 online agent and task search reports 11 tasks.
- **Expected:** Health page should either label these fields as legacy/runtime-only counters or combine `/v1/health` with ACN/task-search summaries.
- **Actual:** Raw JSON can make the system look empty or disconnected.
- **Fix required:** Yes — Phase 07-02.

### F-02 — Live task board contains old E2E/test artifacts

- **Severity:** Low
- **Category:** Data hygiene / Ops
- **Route:** `/dashboard/tasks`
- **Endpoint:** `/v1/tasks/search?page=1&limit=100`
- **Observed:** Live board includes old tasks named `E2E Kanban ...` and `E2E Workflow Canvas ...`.
- **Expected:** Production/live smoke tests should either clean up after themselves, use a hidden test namespace, or document test artifacts explicitly.
- **Actual:** The board is truthful but noisy.
- **Fix required:** Yes, but not as a UI truth bug. Handle as data hygiene/test cleanup policy.

### F-03 — Agents page ACN fallback is acceptable but should remain guarded

- **Severity:** Low
- **Category:** Regression guard
- **Route:** `/dashboard/agents`
- **Endpoint:** `/v1/acn/status`, fallback `/v1/agents/discover/available`
- **Observed:** ACN endpoint returns 1 agent; fallback endpoint returns 0. UI correctly uses ACN first and shows 1.
- **Expected:** Keep ACN-first behavior; avoid future regressions to legacy fallback when ACN is healthy.
- **Actual:** Correct today.
- **Fix required:** No immediate fix; add regression coverage only if touching this path.

## Recommended Phase 07-02 scope

1. Replace raw Health page JSON with a small operational health summary:
   - API health from `/v1/health`
   - ACN nodes/agents from `/v1/acn/status` or `/v1/acn/health`
   - Task totals from `/v1/tasks/search?page=1&limit=1` or a backend summary endpoint
   - Keep raw JSON collapsible/debug-only.
2. Add a frontend test that proves Health page does not present `agents.connected=0` as the sole agent truth when ACN reports agents online.
3. Add a cleanup policy for E2E-created live tasks, or update E2E tests to clean up/archive their own artifacts.

## Commands used

- `curl` public/local health and ACN endpoints
- Authenticated Python API probe using admin credentials from local `.env` without printing secrets
- Authenticated Playwright browser smoke using credentials from local `.env` without printing secrets
- Source inspection of dashboard routes and query hooks
