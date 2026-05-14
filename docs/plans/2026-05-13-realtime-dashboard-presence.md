# Real-time Dashboard Presence Implementation Plan

> **For Hermes:** Use test-driven-development while implementing each behavior.

**Goal:** Wire ACN node/agent/task changes into the existing `/v1/ws/ui` dashboard WebSocket so the command center updates immediately while polling remains a safe fallback.

**Architecture:** OpenHub already has `ConnectionManager`, `/v1/ws/ui`, and a React `useWebSocketSync` hook. This slice reuses that infrastructure: ACN routes emit canonical UI events through `request.app.state.connection_manager.broadcast_to_ui`, and the frontend invalidates or patches TanStack Query caches when those events arrive.

**Tech Stack:** FastAPI, pytest, React/Vite, TanStack Query, existing OpenHub WebSocket manager.

---

## Task 1: Backend ACN event broadcaster helper

**Objective:** Add one safe helper in `app/api/routes_acn.py` so ACN route handlers can broadcast to UI clients without duplicating `getattr`/try/except logic.

**Files:**
- Modify: `app/api/routes_acn.py`
- Test: `tests/unit/test_acn_ws_events.py`

**Events:**
- `acn_node_registered`
- `acn_node_heartbeat`
- `acn_agent_registered`
- `agent_status_changed` for ACN agent heartbeat/registration
- `task_status_changed` for ACN task create/claim/start/complete/fail

## Task 2: Frontend event cache handling

**Objective:** Teach `useWebSocketSync` to handle ACN-specific events and invalidate the right caches.

**Files:**
- Modify: `web/src/hooks/useWebSocketSync.ts`
- Test: `web/src/hooks/useWebSocketSync.test.ts`

**Expected behavior:**
- ACN node/agent events invalidate `qk.agents.all`.
- ACN task events invalidate `qk.tasks.all` and relevant task detail when possible.
- Existing status-patch behavior remains intact.

## Task 3: QA and closeout

**Objective:** Verify backend, frontend, live API health, then commit and push.

**Commands:**
```bash
source .venv/bin/activate && pytest tests/unit/test_acn_ws_events.py tests/unit/test_connection_manager.py tests/unit/test_acn_node_heartbeat.py
cd web && npm run test -- useWebSocketSync.test.ts --run
cd web && npm run typecheck && npm run build
curl -sS http://localhost:7788/v1/health
```

**Closeout:**
```bash
git add app tests web docs
git commit -m "feat(ws): stream ACN presence events to dashboard"
git push origin master
```
