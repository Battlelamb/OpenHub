# OpenHub Coordination Backend Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Turn today’s competitive research and architecture decisions into a staged OpenHub roadmap that makes OpenHub the verification-first coordination backend for AI coding agents.

**Architecture:** Keep Python/FastAPI as the authoritative control plane for tasks, registry, ACN, verification, MCP/API, and durable state. Keep TypeScript/React as the dashboard and live UX layer. Add function-specific services only when a boundary is crisp: Go for local bridge/daemon/process monitoring, Rust only for future safety/performance-critical sandbox/runtime pieces.

**Tech Stack:** FastAPI, Pydantic, Turso/libSQL/SQLite, pytest, React/Vite/TypeScript, TanStack Query, WebSocket/SSE, MCP, optional future Go bridge daemon.

---

## Source Decisions Captured Today

This plan consolidates decisions from the Reddit/Hermes + Claude Code review and competitive scan captured in:

- `docs/COMPETITIVE_METHODS_AND_ARCHITECTURE_NOTES.md`
- Hermes skill: `openhub-competitive-methods`
- Existing strategic docs:
  - `docs/ROADMAP_V2.md`
  - `docs/MULTI_AGENT_HUB_SPEC.md`
  - `docs/AGENT_ONBOARDING.md`
  - `docs/ARCHITECTURE_EVALUATION.md`

## North Star

OpenHub must not be positioned as merely another Claude Code Kanban board.

Preferred positioning:

> OpenHub is the coordination backend for AI coding agents: registry, task routing, verification gates, live dashboard, and MCP/API access for humans and agents working across machines.

Short form:

> Not another coding agent. The coordination layer for all of them.

## Non-Negotiable Design Rules

1. **Task completion requires evidence.** An agent saying “done” is not enough.
2. **Claimed completion and verified completion are different states.**
3. **Humans stay in control.** Risky security/auth/db/deploy work requires review gates.
4. **OpenHub owns authoritative state.** Dashboard, CLI, bridge, and MCP are clients of the same API/state model.
5. **Agent status must be truthful.** Heartbeat freshness and live session events determine status, not stale rows.
6. **Core state ownership must not be split across services.** Python/FastAPI owns tasks/agents/events; other services report events through contracts.
7. **Secrets never enter docs, logs, registry metadata, or chat.** Redact `ak_...`, `oh_...`, bearer tokens, DB URLs, and provider keys.
8. **Microservices only after a crisp boundary exists.** Prefer modular monolith first, service boundary ready.
9. **Every behavior change gets tests before implementation.**
10. **Small commits, staged rollout, test-first.**

---

## Target Product Shape

### Core Surfaces

- REST API for every primitive.
- Dashboard for humans.
- MCP tools/resources for coding agents.
- CLI/onboarding snippets for local workflows.
- WebSocket/SSE event stream for live UI and bridge clients.

### Core Concepts

```text
AgentProvider
AgentRuntime
AgentSession
AgentEvent
AgentCapability
AgentCredential
TaskEvidence
VerificationRun
ReviewGate
CoordinationMessage
WorktreeSession
```

### Target Task Lifecycle

```text
queued
claimed
running
blocked
completed_claimed
verification_running
needs_review
verified
failed
stale
cancelled
```

Compatibility note: if existing API/UI still uses `pending`, `in_progress`, `completed`, or `failed`, add aliases/migrations in stages rather than breaking the dashboard.

### Target Agent State Vocabulary

```text
offline
online
idle
working
blocked
needs_approval
stale
failed
recovering
```

Status must be derived from:

- `last_heartbeat`
- active task/session events
- bridge process events
- task assignment state
- approval/review blockers

---

# Phase 0: Documentation + Roadmap Alignment

## Task 0.1: Commit today’s competitive methods document

**Objective:** Preserve the research and decisions already written today.

**Files:**
- Add: `docs/COMPETITIVE_METHODS_AND_ARCHITECTURE_NOTES.md`

**Steps:**

1. Review the new document:
   ```bash
   sed -n '1,260p' docs/COMPETITIVE_METHODS_AND_ARCHITECTURE_NOTES.md
   ```
2. Confirm no secrets are present:
   ```bash
   grep -RInE '(ak_|oh_|Bearer |token=|TURSO|DATABASE_URL|API_KEY|SECRET)' docs/COMPETITIVE_METHODS_AND_ARCHITECTURE_NOTES.md || true
   ```
   Expected: no secret values.
3. Commit:
   ```bash
   git add docs/COMPETITIVE_METHODS_AND_ARCHITECTURE_NOTES.md
   git commit -m "docs: capture competitive methods and architecture notes"
   ```
4. Push:
   ```bash
   git push origin HEAD
   ```

**Verification:**

```bash
git status --short --branch
git log --oneline -3
```

Expected: branch clean or only intentional next-plan files remain.

---

## Task 0.2: Update roadmap priorities with today’s decisions

**Objective:** Make `ROADMAP_V2.md` reflect the new verification-first direction and remove/soften the old “full Rust rewrite” implication.

**Files:**
- Modify: `docs/ROADMAP_V2.md`
- Reference: `docs/COMPETITIVE_METHODS_AND_ARCHITECTURE_NOTES.md`

**Changes:**

1. Add a new P0 item near the top:
   ```markdown
   ### P0.x: Verification-First Task Lifecycle
   - Separate `completed_claimed` from `verified`.
   - Require evidence bundles before task closure.
   - Add automatic verification for low-risk work.
   - Add human review gates for security/auth/db/deploy tasks.
   ```
2. Add `Task Evidence` before or beside `Artifact / Dosya Paylasimi`.
3. Add `Agent state vocabulary` under Core.
4. Replace the “Rust Rewrite” section with:
   ```markdown
   ## Function-Specific Language Strategy
   Python/FastAPI remains the control plane. Go/Rust services are considered only for crisp runtime boundaries such as bridge daemon, sandbox helper, PTY/log collector, or secure credential helper.
   ```

**Test:** documentation-only.

**Verification:**

```bash
grep -n "Verification-First\|Function-Specific Language" docs/ROADMAP_V2.md
git diff -- docs/ROADMAP_V2.md
```

**Commit:**

```bash
git add docs/ROADMAP_V2.md
git commit -m "docs: align roadmap with verification-first coordination"
```

---

## Task 0.3: Update public positioning copy

**Objective:** Make the README/home copy say OpenHub is the coordination backend, not just a task board.

**Files:**
- Inspect/modify: `README.md`
- Inspect/modify if present: frontend landing/dashboard copy under `web/src/`

**Steps:**

1. Locate current positioning text:
   ```bash
   grep -RIn "Kanban\|agent hub\|coordination\|Claude" README.md docs web/src | head -80
   ```
2. Add the canonical positioning:
   ```markdown
   OpenHub is the coordination backend for AI coding agents: registry, task routing, verification gates, live dashboard, and MCP/API access for humans and agents working across machines.
   ```
3. Add short tagline:
   ```markdown
   Not another coding agent. The coordination layer for all of them.
   ```

**Verification:**

```bash
grep -RIn "coordination backend\|coordination layer" README.md web/src docs | head -20
```

**Commit:**

```bash
git add README.md web/src docs
git commit -m "docs: clarify OpenHub coordination backend positioning"
```

---

# Phase 1: Evidence-First Task Model

## Task 1.1: Inventory current task schema and lifecycle

**Objective:** Understand current task state fields before adding evidence/verification concepts.

**Files:**
- Inspect: `app/models/tasks.py`
- Inspect: `app/database/models.py`
- Inspect: `app/database/repositories/tasks.py`
- Inspect: `app/services/task_service.py`
- Inspect: `app/api/routes_tasks.py`
- Inspect: `tests/integration/test_task_lifecycle.py`

**Commands:**

```bash
sed -n '1,260p' app/models/tasks.py
sed -n '1,260p' app/database/repositories/tasks.py
sed -n '1,260p' app/services/task_service.py
sed -n '1,260p' app/api/routes_tasks.py
sed -n '1,240p' tests/integration/test_task_lifecycle.py
```

**Output:** Add a short note to this plan or a new implementation note listing:

- existing statuses
- existing completion endpoint/body
- where migrations live
- which tests already cover lifecycle

**Commit:** no commit unless a doc note is created.

---

## Task 1.2: Add task evidence model tests

**Objective:** Define what an evidence bundle is before implementing storage.

**Files:**
- Create: `tests/unit/test_task_evidence_model.py`
- Modify later: `app/models/tasks.py`

**Test cases:**

1. Evidence accepts safe fields:
   - `kind`: `test`, `log`, `diff`, `artifact`, `pr`, `review`, `command`
   - `summary`
   - `uri` optional
   - `metadata` optional
   - `created_by_agent_id`
   - `created_at`
2. Evidence rejects/normalizes unsafe raw secret-like metadata keys.
3. Evidence requires at least `kind` and `summary`.
4. Evidence can attach to a `task_id`.

**Example test skeleton:**

```python
from app.models.tasks import TaskEvidenceCreate


def test_task_evidence_requires_kind_and_summary():
    evidence = TaskEvidenceCreate(kind="test", summary="pytest tests/unit -q: 42 passed")
    assert evidence.kind == "test"
    assert "42 passed" in evidence.summary


def test_task_evidence_rejects_secret_metadata_keys():
    evidence = TaskEvidenceCreate(
        kind="log",
        summary="safe log excerpt",
        metadata={"api_key": "[REDACTED]", "exit_code": 0},
    )
    assert evidence.metadata["api_key"] == "[REDACTED]"
```

**Run:**

```bash
pytest tests/unit/test_task_evidence_model.py -q
```

Expected before implementation: FAIL.

---

## Task 1.3: Implement task evidence Pydantic models

**Objective:** Add typed evidence request/response models.

**Files:**
- Modify: `app/models/tasks.py`
- Optional helper: `app/models/base.py` if shared redaction exists

**Implementation notes:**

Add models similar to:

```python
class TaskEvidenceCreate(BaseModel):
    kind: Literal["test", "log", "diff", "artifact", "pr", "review", "command"]
    summary: str
    uri: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

class TaskEvidence(TaskEvidenceCreate):
    id: str
    task_id: str
    created_by_agent_id: str | None = None
    created_at: datetime
```

Add secret-safe metadata sanitation. Do not store raw token-like values.

**Run:**

```bash
pytest tests/unit/test_task_evidence_model.py -q
```

Expected: PASS.

**Commit:**

```bash
git add app/models/tasks.py tests/unit/test_task_evidence_model.py
git commit -m "feat(tasks): add typed evidence models"
```

---

## Task 1.4: Add evidence persistence migration

**Objective:** Store evidence bundles durably.

**Files:**
- Modify: `app/database/migrations.py`
- Modify/create repository method: `app/database/repositories/tasks.py` or new `app/database/repositories/task_evidence.py`
- Add tests: `tests/unit/test_task_evidence_repository.py`

**Schema candidate:**

```sql
CREATE TABLE IF NOT EXISTS task_evidence (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    summary TEXT NOT NULL,
    uri TEXT,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_by_agent_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(task_id) REFERENCES tasks(id)
);

CREATE INDEX IF NOT EXISTS idx_task_evidence_task_id ON task_evidence(task_id);
CREATE INDEX IF NOT EXISTS idx_task_evidence_kind ON task_evidence(kind);
```

**Tests:**

- create evidence for task
- list evidence by task
- evidence survives repository roundtrip
- metadata JSON is safe and valid

**Run:**

```bash
pytest tests/unit/test_task_evidence_repository.py -q
```

**Commit:**

```bash
git add app/database/migrations.py app/database/repositories tests/unit/test_task_evidence_repository.py
git commit -m "feat(tasks): persist task evidence bundles"
```

---

## Task 1.5: Add evidence API endpoints

**Objective:** Let agents and dashboard submit/read evidence.

**Files:**
- Modify: `app/api/routes_tasks.py`
- Modify: `app/services/task_service.py`
- Test: `tests/integration/test_task_lifecycle.py` or new `tests/integration/test_task_evidence_api.py`

**Endpoints:**

```text
POST /v1/tasks/{task_id}/evidence
GET  /v1/tasks/{task_id}/evidence
```

**Rules:**

- Authenticated agents can submit evidence for tasks they own or are allowed to update.
- Admin/dashboard can read evidence.
- Response never includes raw secrets.
- Evidence submission should broadcast a UI event if connection manager is available.

**Tests:**

- submit evidence returns `201` or `200`
- list returns submitted evidence
- unknown task returns `404`
- unauthorized agent cannot attach evidence to another task unless policy allows

**Run:**

```bash
pytest tests/integration/test_task_evidence_api.py -q
pytest tests/integration/test_task_lifecycle.py -q
```

**Commit:**

```bash
git add app/api/routes_tasks.py app/services/task_service.py tests/integration/test_task_evidence_api.py
git commit -m "feat(tasks): expose evidence submission API"
```

---

# Phase 2: Verification Gate

## Task 2.1: Add verification state tests

**Objective:** Prevent tasks from going directly from running/completed to final done without verification.

**Files:**
- Modify/create: `tests/integration/test_task_verification_lifecycle.py`
- Modify later: `app/models/tasks.py`, `app/services/task_service.py`, `app/api/routes_tasks.py`

**Test scenarios:**

1. Agent completes a task with no evidence.
   - Expected: task becomes `completed_claimed` or `needs_review`, not `verified`.
2. Agent completes with evidence and auto-verification policy passes.
   - Expected: task can become `verified`.
3. Security/auth/db/deploy tagged task always requires human review.
   - Expected: `needs_review` until admin approval.
4. Failed verification moves task to `failed` or `needs_review` with reason.

**Run:**

```bash
pytest tests/integration/test_task_verification_lifecycle.py -q
```

Expected before implementation: FAIL.

---

## Task 2.2: Implement verification policy classifier

**Objective:** Centralize which tasks require automatic verification vs human review.

**Files:**
- Create: `app/services/verification_policy.py`
- Create: `tests/unit/test_verification_policy.py`

**Policy inputs:**

- task title/description/tags
- changed files if available
- evidence kinds submitted
- agent capability/trust level if available

**Initial policy:**

```text
Requires human review if:
- task tags include security/auth/database/deploy/secrets
- changed files include auth, migrations, config, deployment, env, CI
- evidence is missing

Auto-verifiable if:
- low-risk docs/UI/test-only change
- required evidence exists
- verification command exits 0
```

**Run:**

```bash
pytest tests/unit/test_verification_policy.py -q
```

**Commit:**

```bash
git add app/services/verification_policy.py tests/unit/test_verification_policy.py
git commit -m "feat(verification): add task review policy classifier"
```

---

## Task 2.3: Add verification run model and persistence

**Objective:** Track verification attempts independently from task state.

**Files:**
- Modify: `app/models/tasks.py`
- Modify: `app/database/migrations.py`
- Create/modify repository: `app/database/repositories/task_verification.py` or `tasks.py`
- Test: `tests/unit/test_task_verification_repository.py`

**Schema candidate:**

```sql
CREATE TABLE IF NOT EXISTS task_verification_runs (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    status TEXT NOT NULL,
    policy_result TEXT NOT NULL,
    command TEXT,
    output_summary TEXT,
    exit_code INTEGER,
    reviewer_agent_id TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY(task_id) REFERENCES tasks(id)
);

CREATE INDEX IF NOT EXISTS idx_task_verification_runs_task_id ON task_verification_runs(task_id);
```

**Run:**

```bash
pytest tests/unit/test_task_verification_repository.py -q
```

**Commit:**

```bash
git add app/models/tasks.py app/database/migrations.py app/database/repositories tests/unit/test_task_verification_repository.py
git commit -m "feat(verification): persist verification runs"
```

---

## Task 2.4: Wire task completion through verification gate

**Objective:** Change completion flow so `complete` means “claimed complete”, then verification/review decides final state.

**Files:**
- Modify: `app/services/task_service.py`
- Modify: `app/api/routes_tasks.py`
- Modify tests: `tests/integration/test_task_lifecycle.py`, `tests/integration/test_task_verification_lifecycle.py`

**Rules:**

- Existing complete endpoint remains backward-compatible if necessary.
- Internally, completion produces `completed_claimed`.
- If policy says auto-verify and required evidence exists, create `verification_running` then `verified`.
- If policy says review, set `needs_review`.
- If verification fails, set `needs_review` or `failed` with reason.

**Run:**

```bash
pytest tests/integration/test_task_lifecycle.py -q
pytest tests/integration/test_task_verification_lifecycle.py -q
```

**Commit:**

```bash
git add app/services/task_service.py app/api/routes_tasks.py tests/integration/test_task_lifecycle.py tests/integration/test_task_verification_lifecycle.py
git commit -m "feat(tasks): route completion through verification gate"
```

---

## Task 2.5: Add admin/human review endpoints

**Objective:** Let humans approve/reject claimed work from dashboard or API.

**Files:**
- Modify: `app/api/routes_tasks.py`
- Modify: `app/services/task_service.py`
- Test: `tests/integration/test_task_review_api.py`

**Endpoints:**

```text
POST /v1/tasks/{task_id}/review/approve
POST /v1/tasks/{task_id}/review/reject
```

**Rules:**

- Requires admin/reviewer privileges.
- Approve moves `needs_review` -> `verified`.
- Reject moves `needs_review` -> `failed` or `blocked` with reason.
- Creates verification/review evidence.
- Broadcasts UI event.

**Run:**

```bash
pytest tests/integration/test_task_review_api.py -q
```

**Commit:**

```bash
git add app/api/routes_tasks.py app/services/task_service.py tests/integration/test_task_review_api.py
git commit -m "feat(tasks): add human review gate endpoints"
```

---

# Phase 3: Truthful Agent State + Event Vocabulary

## Task 3.1: Define canonical event types

**Objective:** Normalize agent/session/task events so dashboard, bridge, MCP, and verification all speak one language.

**Files:**
- Modify: `app/models/events.py`
- Test: `tests/unit/test_event_types.py`

**Event types:**

```text
session.started
session.ended
command.started
command.finished
file.changed
task.claimed
task.started
task.blocked
approval.requested
evidence.submitted
task.completed_claimed
verification.started
verification.finished
task.verified
task.failed
agent.heartbeat
agent.status_changed
```

**Run:**

```bash
pytest tests/unit/test_event_types.py -q
```

**Commit:**

```bash
git add app/models/events.py tests/unit/test_event_types.py
git commit -m "feat(events): define canonical coordination event types"
```

---

## Task 3.2: Add agent state classifier tests

**Objective:** Derive user-facing state from heartbeat + active work + blockers.

**Files:**
- Create: `tests/unit/test_agent_state_classifier.py`
- Create/modify: `app/services/agent_state.py`
- Possibly modify: `app/services/heartbeat_service.py`, `app/services/remote_agent_service.py`

**Scenarios:**

- fresh heartbeat, no task => `idle`
- fresh heartbeat, running task => `working`
- task blocked => `blocked`
- approval requested => `needs_approval`
- stale heartbeat => `stale` or `offline`
- failed bridge/session event => `failed`

**Run:**

```bash
pytest tests/unit/test_agent_state_classifier.py -q
```

**Commit:**

```bash
git add app/services/agent_state.py tests/unit/test_agent_state_classifier.py
git commit -m "feat(agents): classify rich agent states"
```

---

## Task 3.3: Expose rich state in ACN/agents APIs

**Objective:** Let dashboard and MCP see rich agent state without guessing.

**Files:**
- Modify: `app/api/routes_acn.py`
- Modify: `app/api/routes_agents.py`
- Modify: `app/models/agents.py`
- Test: `tests/unit/test_acn_node_heartbeat.py`, `tests/integration/test_agent_lifecycle.py`

**Response fields:**

```json
{
  "status": "online",
  "state": "working",
  "state_reason": "running_task",
  "last_heartbeat": "...",
  "current_task_id": "...",
  "needs_approval_count": 0,
  "stale_after_seconds": 300
}
```

**Run:**

```bash
pytest tests/unit/test_acn_node_heartbeat.py -q
pytest tests/integration/test_agent_lifecycle.py -q
```

**Commit:**

```bash
git add app/api/routes_acn.py app/api/routes_agents.py app/models/agents.py tests/unit/test_acn_node_heartbeat.py tests/integration/test_agent_lifecycle.py
git commit -m "feat(agents): expose rich runtime state"
```

---

# Phase 4: Live Task Detail Dashboard

## Task 4.1: Add frontend types and API hooks for evidence/verification

**Objective:** Let React consume evidence and verification state with typed hooks.

**Files:**
- Modify: `web/src/types/entities.ts`
- Modify: `web/src/lib/query-keys.ts`
- Create: `web/src/hooks/queries/useTaskEvidence.ts`
- Create: `web/src/hooks/queries/useTaskVerification.ts`
- Tests: matching `.test.ts` files

**Run:**

```bash
cd web
npm test -- --run useTaskEvidence useTaskVerification
npm run typecheck
```

**Commit:**

```bash
git add web/src/types/entities.ts web/src/lib/query-keys.ts web/src/hooks/queries
git commit -m "feat(web): add task evidence and verification hooks"
```

---

## Task 4.2: Build evidence panel on task detail page

**Objective:** Show proof, not just status.

**Files:**
- Modify: `web/src/routes/_authed/tasks/$taskId.tsx`
- Create optional component: `web/src/components/common/TaskEvidencePanel.tsx`
- Test: `web/src/components/common/TaskEvidencePanel.test.tsx`

**Panel contents:**

- task state
- evidence list grouped by kind
- test/log/diff/artifact/PR links
- verification runs
- review decision
- empty state: “No evidence submitted yet.”

**Run:**

```bash
cd web
npm test -- --run TaskEvidencePanel
npm run typecheck
npm run build
```

**Commit:**

```bash
git add web/src/routes/_authed/tasks/$taskId.tsx web/src/components/common/TaskEvidencePanel.tsx web/src/components/common/TaskEvidencePanel.test.tsx
git commit -m "feat(web): show task evidence and verification timeline"
```

---

## Task 4.3: Add human review controls

**Objective:** Let an admin approve/reject `needs_review` tasks in the UI.

**Files:**
- Modify: `web/src/routes/_authed/tasks/$taskId.tsx`
- Create optional component: `web/src/components/common/TaskReviewControls.tsx`
- Test: `web/src/components/common/TaskReviewControls.test.tsx`

**Rules:**

- Controls only appear for `needs_review`.
- Approve/reject requires confirmation.
- Rejection requires reason.
- UI invalidates task/evidence/verification queries.

**Run:**

```bash
cd web
npm test -- --run TaskReviewControls
npm run typecheck
npm run build
```

**Commit:**

```bash
git add web/src/routes/_authed/tasks/$taskId.tsx web/src/components/common/TaskReviewControls.tsx web/src/components/common/TaskReviewControls.test.tsx
git commit -m "feat(web): add task review controls"
```

---

## Task 4.4: Broadcast live evidence and verification events

**Objective:** Make task detail update live without refresh.

**Files:**
- Modify: `app/services/connection_manager.py`
- Modify: `app/api/routes_ws_ui.py` if needed
- Modify: `web/src/hooks/useWebSocketSync.ts` or equivalent existing sync hook
- Test: `tests/unit/test_acn_ws_events.py` and frontend WebSocket sync tests if present

**Events:**

```text
evidence.submitted
verification.started
verification.finished
task.needs_review
task.verified
task.failed
```

**Run:**

```bash
pytest tests/unit/test_acn_ws_events.py -q
cd web && npm run typecheck && npm run build
```

**Commit:**

```bash
git add app/services/connection_manager.py app/api/routes_ws_ui.py web/src tests/unit/test_acn_ws_events.py
git commit -m "feat(realtime): broadcast evidence and verification updates"
```

---

# Phase 5: Agent Onboarding + MCP-First Access

## Task 5.1: Rewrite onboarding snippets for agents

**Objective:** Give Claude Code, Codex, Hermes, Cursor, OpenCode, and other agents copy-paste instructions for using OpenHub safely.

**Files:**
- Modify: `docs/AGENT_ONBOARDING.md`
- Optional create: `docs/snippets/AGENTS.openhub.md`
- Optional create: `docs/snippets/CLAUDE.openhub.md`
- Optional create: `docs/snippets/HERMES.openhub.md`

**Snippet must include:**

- how to join/register
- how to claim task
- heartbeat/status behavior
- evidence submission requirement
- when to mark blocked/needs_review
- never print secrets
- no direct DB writes
- use API/MCP/CLI primitives

**Verification:**

```bash
grep -RIn "evidence\|needs_review\|heartbeat\|secrets" docs/AGENT_ONBOARDING.md docs/snippets || true
```

**Commit:**

```bash
git add docs/AGENT_ONBOARDING.md docs/snippets
git commit -m "docs: add verification-first agent onboarding snippets"
```

---

## Task 5.2: Define MCP tool contract for task/evidence/registry

**Objective:** Make MCP a first-class client surface, not a side experiment.

**Files:**
- Modify: `docs/agent-mcp-profiles.md`
- Optional create: `docs/MCP_TOOL_CONTRACT.md`

**Tools/resources:**

```text
openhub.list_tasks
openhub.read_task
openhub.claim_task
openhub.release_task
openhub.start_task
openhub.submit_evidence
openhub.mark_blocked
openhub.request_review
openhub.read_agent_registry
openhub.send_message
openhub.search_memory
openhub.read_event_snapshot
```

**Contract requirements:**

- Every mutating tool maps to REST API.
- Tool errors include safe reason, never secrets.
- MCP cannot bypass auth/policy.
- Evidence and verification semantics match REST/dashboard.

**Verification:** documentation-only.

**Commit:**

```bash
git add docs/agent-mcp-profiles.md docs/MCP_TOOL_CONTRACT.md
git commit -m "docs: define OpenHub MCP task coordination contract"
```

---

## Task 5.3: Implement minimal MCP adapter only after REST is stable

**Objective:** Add MCP task/evidence tools by wrapping existing service/API logic.

**Files:**
- Inspect current MCP code first; if none, create under `app/mcp/` or `scripts/` according to project conventions.
- Tests: new MCP contract tests.

**Do not implement until:**

- task evidence REST endpoints pass
- verification lifecycle tests pass
- onboarding docs are updated

**Acceptance:**

- `list_tasks`, `claim_task`, `submit_evidence`, and `read_agent_registry` work first.
- No separate MCP database/state.

**Commit:**

```bash
git add app/mcp tests docs
git commit -m "feat(mcp): expose task coordination primitives"
```

---

# Phase 6: Worktree / Session Isolation

## Task 6.1: Add worktree/session metadata model

**Objective:** Track coding tasks safely across parallel agents and worktrees.

**Files:**
- Modify: `app/models/tasks.py`
- Modify: `app/database/migrations.py`
- Modify: `app/database/repositories/tasks.py`
- Test: `tests/unit/test_task_worktree_metadata.py`

**Fields:**

```text
repo_path
base_branch
task_branch
worktree_path
session_id
provider
pr_url
changed_files
```

**Rules:**

- metadata is optional for non-coding tasks
- paths are stored as metadata, not blindly executed
- no secrets in repo URLs

**Run:**

```bash
pytest tests/unit/test_task_worktree_metadata.py -q
```

**Commit:**

```bash
git add app/models/tasks.py app/database/migrations.py app/database/repositories/tasks.py tests/unit/test_task_worktree_metadata.py
git commit -m "feat(tasks): track worktree and session metadata"
```

---

## Task 6.2: Show worktree/session metadata in task detail

**Objective:** Make parallel coding work auditable.

**Files:**
- Modify: `web/src/routes/_authed/tasks/$taskId.tsx`
- Optional component: `web/src/components/common/TaskSessionPanel.tsx`
- Test: `web/src/components/common/TaskSessionPanel.test.tsx`

**Display:**

- agent/session
- provider/runtime
- repo/base branch/task branch
- worktree path
- PR link
- changed files

**Run:**

```bash
cd web
npm test -- --run TaskSessionPanel
npm run typecheck
npm run build
```

**Commit:**

```bash
git add web/src/routes/_authed/tasks/$taskId.tsx web/src/components/common/TaskSessionPanel.tsx web/src/components/common/TaskSessionPanel.test.tsx
git commit -m "feat(web): show task worktree session metadata"
```

---

# Phase 7: Function-Specific Language Strategy

## Task 7.1: Add architecture decision record for polyglot boundaries

**Objective:** Record the language/microservice decision so future agents do not randomly rewrite the core.

**Files:**
- Create: `docs/adr/2026-05-17-function-specific-language-boundaries.md`
- Reference: `docs/COMPETITIVE_METHODS_AND_ARCHITECTURE_NOTES.md`

**Decision text:**

- Python/FastAPI remains control plane.
- TypeScript remains dashboard/UI.
- Go is candidate for local bridge/daemon/process monitor.
- Rust is reserved for sandbox/PTY/credential/log collector if needed.
- Node/TypeScript backend only for JS-first extension/adapters.
- No service may own task state except the core API/database layer.

**Verification:**

```bash
grep -RIn "Python/FastAPI remains the control plane\|Go is candidate\|Rust is reserved" docs/adr
```

**Commit:**

```bash
git add docs/adr/2026-05-17-function-specific-language-boundaries.md
git commit -m "docs: record function-specific language boundaries"
```

---

## Task 7.2: Write Go bridge RFC before implementation

**Objective:** Design the future Go bridge as a narrow sidecar, not a second backend.

**Files:**
- Create: `docs/rfc/go-agent-bridge-daemon.md`

**RFC must answer:**

- What problem does Go solve that Python bridge cannot?
- Install target: Linux/macOS/Windows?
- API contract to core: `/v1/events`, `/v1/agents/heartbeat`, `/v1/tasks/poll`?
- Secret storage: env file/keychain? How to avoid logs?
- Health check and self-update model.
- What stays in Python core.
- When to stop and keep Python bridge.

**Initial boundary:**

```text
Go daemon reports process/session/heartbeat/file events.
Python API owns task lifecycle, verification, registry, and persistence.
```

**Commit:**

```bash
git add docs/rfc/go-agent-bridge-daemon.md
git commit -m "docs: propose Go bridge daemon boundary"
```

---

## Task 7.3: Add bridge event contract tests before Go exists

**Objective:** Make the core API contract ready for any future bridge implementation.

**Files:**
- Create: `tests/integration/test_bridge_event_contract.py`
- Modify if needed: `app/api/routes_acn.py` or new event route

**Contract:**

```json
{
  "event_type": "command.finished",
  "agent_id": "...",
  "task_id": "...",
  "session_id": "...",
  "occurred_at": "...",
  "payload": {
    "exit_code": 0,
    "summary": "pytest passed"
  }
}
```

**Rules:**

- accepted event types validated
- payload redacted/sanitized
- event can update derived agent/task state
- event can create evidence when type is evidence-like

**Run:**

```bash
pytest tests/integration/test_bridge_event_contract.py -q
```

**Commit:**

```bash
git add app/api tests/integration/test_bridge_event_contract.py
git commit -m "feat(events): add bridge event ingestion contract"
```

---

# Phase 8: Operational Hardening and Release Gate

## Task 8.1: Add operational snapshot command/doc

**Objective:** Before major OpenHub work, produce a standard snapshot: repo, API health, bridge, DB counts, stale tasks, tests.

**Files:**
- Create or modify: `docs/OPERATIONS_SNAPSHOT.md`
- Optional script: `scripts/openhub_snapshot.py`

**Snapshot includes:**

- git branch/status/remote
- API `/v1/health` and `/v1/health/simple`
- ACN health/status if running
- runtime DB backend presence without secrets
- task counts by status
- agents fresh vs stale
- bridge log tail redacted

**Verification:**

```bash
python scripts/openhub_snapshot.py --redact
```

Expected: safe output, no secrets.

**Commit:**

```bash
git add docs/OPERATIONS_SNAPSHOT.md scripts/openhub_snapshot.py
git commit -m "chore(ops): add redacted OpenHub snapshot command"
```

---

## Task 8.2: Add task queue hygiene checks

**Objective:** Make stale claimed/running tasks visible before new work starts.

**Files:**
- Modify/create: `app/services/task_service.py`
- Add endpoint or script if appropriate
- Test: `tests/unit/test_task_queue_hygiene.py`

**Checks:**

- claimed/running tasks with expired lease
- tasks stuck in `verification_running`
- tasks in `needs_review` longer than threshold
- agents marked online with stale heartbeat

**Run:**

```bash
pytest tests/unit/test_task_queue_hygiene.py -q
```

**Commit:**

```bash
git add app/services/task_service.py tests/unit/test_task_queue_hygiene.py
git commit -m "feat(tasks): detect stale queue states"
```

---

## Task 8.3: Define release checklist for OpenHub features

**Objective:** Make every OpenHub feature ship with tests, docs, evidence, and rollback notes.

**Files:**
- Create: `docs/RELEASE_CHECKLIST.md`

**Checklist:**

- tests added before implementation
- backend tests pass
- frontend typecheck/build pass if UI touched
- migrations reviewed
- secrets scan performed
- evidence submitted for task
- verification/review status recorded
- docs updated
- commit pushed
- public dashboard smoke checked if relevant

**Commit:**

```bash
git add docs/RELEASE_CHECKLIST.md
git commit -m "docs: add OpenHub release checklist"
```

---

# Suggested Sprint Order

## Sprint A — Foundation docs and roadmap

1. Commit competitive methods doc.
2. Update roadmap.
3. Update README positioning.
4. Add ADR for function-specific language boundaries.

**Result:** strategy is durable and future agents follow the same north star.

## Sprint B — Evidence and verification backend

1. Evidence models.
2. Evidence persistence.
3. Evidence API.
4. Verification policy.
5. Verification runs.
6. Completion through verification gate.
7. Human review endpoints.

**Result:** OpenHub’s differentiator becomes real: agents produce verifiable work.

## Sprint C — Dashboard proof surface

1. Frontend types/hooks.
2. Evidence panel.
3. Review controls.
4. Live updates.

**Result:** humans can see the proof and approve/reject work.

## Sprint D — Agent/MCP integration

1. Onboarding snippets.
2. MCP contract.
3. Minimal MCP adapter.
4. Bridge event contract.

**Result:** Claude Code/Codex/Hermes/OpenCode can coordinate through OpenHub without bespoke per-tool hacks.

## Sprint E — Runtime hardening and future Go bridge

1. Rich agent state classifier.
2. Worktree/session metadata.
3. Ops snapshot.
4. Queue hygiene.
5. Go bridge RFC.
6. Bridge event ingestion contract.

**Result:** OpenHub becomes durable enough for multi-agent, cross-machine real work.

---

# Verification Commands for Each Major PR

Backend-only:

```bash
pytest tests/unit -q
pytest tests/integration -q
```

Frontend touched:

```bash
cd web
npm run typecheck
npm run build
npm test -- --run
```

Docs-only:

```bash
grep -RInE '(ak_|oh_|Bearer |token=|API_KEY|SECRET|DATABASE_URL|TURSO)' docs || true
git diff --check
```

Full local safety gate:

```bash
git status --short --branch
pytest tests/unit -q
pytest tests/integration -q
cd web && npm run typecheck && npm run build
```

---

# Acceptance Criteria for This Plan

OpenHub will be aligned with today’s decisions when:

- [ ] `docs/COMPETITIVE_METHODS_AND_ARCHITECTURE_NOTES.md` is committed and pushed.
- [ ] Roadmap says verification-first coordination is P0-level.
- [ ] README/product copy says OpenHub is the coordination backend/layer.
- [ ] Task evidence exists in model, DB, API, tests, and UI.
- [ ] Task completion no longer silently equals verified done.
- [ ] Risky tasks require human review.
- [ ] Dashboard task detail shows evidence, verification, and review status.
- [ ] Agents have rich state beyond online/offline.
- [ ] Agent onboarding snippets teach evidence and safe coordination.
- [ ] MCP contract includes task/evidence/registry primitives.
- [ ] Function-specific language ADR prevents premature rewrites.
- [ ] Go bridge is designed by RFC before implementation.
- [ ] Release checklist and ops snapshot make future work verifiable.

---

# Immediate Next Action

Recommended next commit sequence:

```bash
# 1) Commit today's research document
git add docs/COMPETITIVE_METHODS_AND_ARCHITECTURE_NOTES.md docs/plans/2026-05-17-openhub-coordination-backend-plan.md
git commit -m "docs: plan OpenHub verification-first coordination backend"

git push origin HEAD
```

Then start Sprint A with a separate branch/commit for roadmap and README alignment.
