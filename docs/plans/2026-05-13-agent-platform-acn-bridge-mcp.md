# Agent Platform: ACN + Bridge + MCP Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a truthful agent platform where OpenHub/ACN owns registry and presence, Agent Bridge owns real agent connectivity and task execution, and MCP is used only as the tool/integration layer.

**Architecture:** ACN/OpenHub is the control plane: identity, registry, node/agent presence, capabilities, tasks, and audit. Agent Bridge is the runtime connector: authenticated heartbeat, task polling, execution, and result reporting. MCP is the optional tool surface exposed to agents for GitHub, filesystem, databases, internal APIs, and other integrations; MCP must not be the source of truth for online/offline status.

**Tech Stack:** FastAPI backend, Turso/libsql-backed repositories, pytest unit/integration tests, existing OpenHub dashboard frontend, Hermes native MCP configuration for optional MCP tool profiles.

---

## Non-Negotiable Design Rules

1. **Node online does not imply agent online.**
2. **Agent online requires an agent-specific authenticated heartbeat.**
3. **MCP is not the presence layer.** It is only a tool/integration layer.
4. **No secrets in registry metadata.** API keys, Turso tokens, GitHub PATs, Bearer tokens, and MCP credentials stay in node-local env/config.
5. **Old/stale records should be shown truthfully, not silently deleted.**
6. **Every backend behavior change gets a regression test before implementation.**
7. **Small staged commits.** Do not mix frontend polish, backend schema, and MCP integration in one commit.

---

## Phase 1: Truthful Presence Schema

### Task 1: Add tests for explicit node vs agent status fields

**Objective:** Prove that ACN status exposes node and agent state separately.

**Files:**
- Modify: `tests/unit/test_acn_node_heartbeat.py`
- Likely inspect/modify later: `app/api/routes_acn.py`

**Step 1: Add failing test**

Add a test that creates:
- one online node
- one online agent with fresh heartbeat
- one stale/offline agent mapped to the same node

Expected status response/model must be able to represent:
- `node_status: online`
- `agent_status: offline`
- separate `last_node_heartbeat`
- separate `last_agent_heartbeat`

**Step 2: Run test**

```bash
pytest tests/unit/test_acn_node_heartbeat.py -q
```

Expected: FAIL until route/service shape is updated.

**Step 3: Implement minimal response fields**

In `app/api/routes_acn.py`, ensure `/v1/acn/status` agent entries include at minimum:

```json
{
  "agent_id": "agent-1",
  "name": "claude-code",
  "agent_status": "offline",
  "node_id": "node-1",
  "node_name": "brunhilde-vps",
  "node_status": "online",
  "last_agent_heartbeat": "...",
  "last_node_heartbeat": "...",
  "capabilities": []
}
```

Keep backwards-compatible aliases temporarily if the frontend still expects `status` and `last_heartbeat`.

**Step 4: Verify**

```bash
pytest tests/unit/test_acn_node_heartbeat.py -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add app/api/routes_acn.py tests/unit/test_acn_node_heartbeat.py
git commit -m "fix(acn): separate node and agent status fields"
```

---

### Task 2: Add stale/offline TTL tests

**Objective:** Ensure stale agent heartbeats cannot appear online forever.

**Files:**
- Modify: `tests/unit/test_acn_node_heartbeat.py`
- Modify if needed: `app/services/remote_agent_service.py`
- Modify if needed: `app/api/routes_acn.py`

**Step 1: Write failing tests**

Add cases:

1. Fresh agent heartbeat within TTL => `agent_status: online`
2. Old agent heartbeat beyond TTL => `agent_status: stale` or `offline`
3. Node heartbeat fresh but agent heartbeat old => node online, agent offline/stale

Use fixed timestamps where possible.

**Step 2: Run tests**

```bash
pytest tests/unit/test_acn_node_heartbeat.py -q
```

Expected: FAIL if TTL is not explicitly enforced.

**Step 3: Implement minimal TTL helper**

Prefer a small helper in service layer rather than duplicating logic in routes, for example:

```python
def classify_heartbeat_status(last_heartbeat, ttl_seconds: int) -> str:
    if not last_heartbeat:
        return "offline"
    # parse datetime safely
    # return "online" if within ttl else "offline" or "stale"
```

Choose one vocabulary and keep it consistent. Recommendation:
- `online`: actively heartbeating within TTL
- `offline`: no valid heartbeat within TTL
- optional UI reason: `stale_heartbeat`

**Step 4: Verify**

```bash
pytest tests/unit/test_acn_node_heartbeat.py -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add app/services/remote_agent_service.py app/api/routes_acn.py tests/unit/test_acn_node_heartbeat.py
git commit -m "test(acn): enforce stale agent heartbeat classification"
```

---

## Phase 2: Bridge Identity Cleanup

### Task 3: Standardize API key metadata shape

**Objective:** Make every real agent heartbeat traceable to a specific agent identity.

**Files:**
- Modify: `app/auth/api_keys.py`
- Modify: `app/api/routes_acn.py`
- Add/modify tests under `tests/unit/`

**Canonical metadata:**

```json
{
  "agent_id": "agent_x",
  "agent_name": "brunhilde",
  "node_id": "brunhilde-vps",
  "bridge_id": "bridge_x",
  "allowed_capabilities": ["chat", "terminal"]
}
```

**Rules:**
- Metadata may be returned internally after API key validation.
- Metadata must be sanitized.
- Raw key/hash/token must never be returned.
- Missing metadata means heartbeat updates node only, not any agent.

**Step 1: Add tests**

Test that validated key info includes sanitized metadata but no raw secret material.

**Step 2: Run tests**

```bash
pytest tests/unit -q -k "api_key or acn"
```

**Step 3: Implement or harden metadata parsing**

Ensure invalid JSON metadata does not crash request handling. It should safely return `{}` or reject with a controlled auth error.

**Step 4: Verify**

```bash
pytest tests/unit -q -k "api_key or acn"
```

**Step 5: Commit**

```bash
git add app/auth/api_keys.py app/api/routes_acn.py tests/unit
git commit -m "fix(auth): expose sanitized agent metadata for heartbeats"
```

---

### Task 4: Harden `run_bridge.py` registration and heartbeat identity

**Objective:** Ensure each bridge process authenticates and heartbeats as exactly one configured agent.

**Files:**
- Inspect/modify: `scripts/run_bridge.py`
- Inspect/modify: `app/bridge/agent_bridge.py`
- Add tests if bridge has test coverage; otherwise add a focused unit around config parsing.

**Step 1: Inspect current bridge startup**

Check how agent name, node ID, API key, and heartbeat payload are produced.

**Step 2: Add or update test**

Test that bridge config produces:

```json
{
  "agent_name": "brunhilde",
  "node_id": "brunhilde-vps"
}
```

and never sends another agent's identity.

**Step 3: Implement minimal hardening**

Bridge should:
- read one configured agent identity
- use one API key
- heartbeat node endpoint with authenticated key
- not infer online status for other mapped agents

**Step 4: Verify locally**

```bash
pytest tests/unit -q -k "bridge or acn"
```

Then, only with operator approval, restart the live bridge/API if required.

**Step 5: Commit**

```bash
git add scripts/run_bridge.py app/bridge/agent_bridge.py tests/unit
git commit -m "fix(bridge): bind heartbeat to configured agent identity"
```

---

## Phase 3: Capabilities System

### Task 5: Canonicalize agent capabilities

**Objective:** Make OpenHub able to answer: which agent can do this task?

**Files:**
- Modify: agent model/repository files as needed
- Modify: `app/api/routes_acn.py`
- Modify/add tests under `tests/unit/`

**Canonical capability examples:**

```json
[
  "chat",
  "code_review",
  "repo_edit",
  "terminal",
  "browser",
  "github",
  "filesystem",
  "homeassistant",
  "scheduled_jobs"
]
```

**Step 1: Add tests**

Test that capabilities are stored and returned as an array, never as malformed JSON/string.

**Step 2: Implement parser/normalizer**

Use one helper function for capability parsing. Do not duplicate parsing in frontend and backend.

**Step 3: Verify**

```bash
pytest tests/unit -q -k "capabilities or acn"
```

**Step 4: Commit**

```bash
git add app tests
git commit -m "feat(acn): normalize agent capabilities"
```

---

## Phase 4: Minimum Task Routing

### Task 6: Add `agent_tasks` persistence model

**Objective:** Store tasks that can be assigned to agents.

**Files:**
- Create migration under `database/migrations/`
- Create repository under `app/database/repositories/` if repository pattern requires it
- Add tests under `tests/unit/`

**Minimal fields:**

```json
{
  "task_id": "task_x",
  "target_agent_id": "agent_x",
  "status": "queued",
  "prompt": "...",
  "created_at": "...",
  "claimed_at": null,
  "completed_at": null,
  "result": null,
  "error": null
}
```

**Status values:**
- `queued`
- `claimed`
- `running`
- `completed`
- `failed`
- `stale`

**Step 1: Write repository tests**

Tests:
- create queued task
- list queued tasks for target agent
- claim task atomically
- complete task
- fail task

**Step 2: Run tests**

```bash
pytest tests/unit -q -k "agent_tasks"
```

Expected: FAIL.

**Step 3: Add migration and repository**

Keep schema minimal. Avoid advanced scheduling until needed.

**Step 4: Verify**

```bash
pytest tests/unit -q -k "agent_tasks"
```

Expected: PASS.

**Step 5: Commit**

```bash
git add database/migrations app/database/repositories tests/unit
git commit -m "feat(acn): add agent task persistence"
```

---

### Task 7: Add minimal task API endpoints

**Objective:** Allow task creation, polling, claiming, completion, and failure.

**Files:**
- Modify: `app/api/routes_acn.py` or create dedicated `app/api/routes_agent_tasks.py`
- Modify route registration if needed
- Add tests under `tests/unit/` or `tests/integration/`

**Endpoints:**

```text
POST /v1/acn/tasks
GET  /v1/acn/tasks/poll
POST /v1/acn/tasks/{task_id}/claim
POST /v1/acn/tasks/{task_id}/complete
POST /v1/acn/tasks/{task_id}/fail
```

**Step 1: Add API tests**

Tests:
- unauthenticated calls rejected
- agent only polls eligible tasks
- claim is idempotent/atomic
- result is stored on complete
- error is stored on fail

**Step 2: Implement endpoints**

Use authenticated API key metadata to determine agent identity where possible.

**Step 3: Verify**

```bash
pytest tests/unit tests/integration -q -k "tasks or acn"
```

**Step 4: Commit**

```bash
git add app/api tests
git commit -m "feat(acn): add agent task routing endpoints"
```

---

### Task 8: Add bridge task polling loop

**Objective:** Make real agent bridge processes claim and complete tasks.

**Files:**
- Modify: `app/bridge/agent_bridge.py`
- Modify: `scripts/run_bridge.py`
- Add tests if practical

**Step 1: Add bridge polling behavior behind a flag**

Feature flag suggestion:

```text
AGENTHUB_TASK_POLLING_ENABLED=true
```

Default may be false until verified.

**Step 2: Implement loop**

Bridge loop should:
1. heartbeat
2. poll task endpoint
3. claim one task
4. execute using local agent adapter
5. complete/fail task with result

**Step 3: Verify with a dry-run adapter first**

Do not connect dangerous terminal/repo edit tools on first pass. Use a dry-run task executor that returns a simple string.

**Step 4: Commit**

```bash
git add app/bridge scripts tests
git commit -m "feat(bridge): add task polling loop"
```

---

## Phase 5: MCP Profiles as Tool Layer

### Task 9: Add MCP profile names to agent metadata/capabilities

**Objective:** Let OpenHub display which MCP tool profiles an agent is configured to use without storing secrets.

**Files:**
- Modify backend metadata/capabilities parsing
- Modify ACN status response
- Add tests

**Registry-safe metadata example:**

```json
{
  "mcp_profiles": ["github", "filesystem", "postgres"]
}
```

**Forbidden in registry:**

```json
{
  "GITHUB_PERSONAL_ACCESS_TOKEN": "...",
  "Authorization": "Bearer ...",
  "DATABASE_URL": "..."
}
```

**Step 1: Add redaction/safety test**

Test that obvious secret-like keys are either rejected or redacted before status output.

**Step 2: Implement mcp profile surface**

Status response may include:

```json
{
  "mcp_profiles": ["github", "filesystem"],
  "tool_families": ["github", "filesystem"]
}
```

**Step 3: Verify**

```bash
pytest tests/unit -q -k "mcp or metadata or acn"
```

**Step 4: Commit**

```bash
git add app tests
git commit -m "feat(acn): expose safe mcp profile metadata"
```

---

### Task 10: Document node-local MCP config

**Objective:** Provide the operator with a safe pattern for MCP configuration.

**Files:**
- Create: `docs/agent-mcp-profiles.md`

**Content requirements:**
- Explain that OpenHub stores profile names only.
- Explain that secrets stay in `~/.hermes/config.yaml`, env vars, or node-local secret manager.
- Include example Hermes MCP config with redacted tokens.

**Example:**

```yaml
mcp_servers:
  github:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "[REDACTED]"

  filesystem:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/home/omer/projects"]
```

**Step 1: Write doc**

**Step 2: Commit**

```bash
git add docs/agent-mcp-profiles.md
git commit -m "docs: add safe mcp profile guidance"
```

---

## Phase 6: Dashboard UX

### Task 11: Show node status and agent status separately

**Objective:** Prevent UI confusion such as “node online therefore stale agent online.”

**Files:**
- Modify: `web/src/hooks/queries/useAgents.ts`
- Modify: `web/src/types/entities.ts`
- Modify: `web/src/routes/_authed/agents/index.tsx`

**UI copy example:**

```text
claude-code: offline
Reason: no agent heartbeat within TTL.
Node brunhilde-vps is online, but this agent is not currently connected.
```

**Step 1: Update types**

Add fields:
- `agentStatus`
- `nodeStatus`
- `lastAgentHeartbeat`
- `lastNodeHeartbeat`
- `offlineReason`
- `mcpProfiles`

**Step 2: Update query mapper**

Map backend snake_case to frontend camelCase.

**Step 3: Update card/table rendering**

Show:
- Agent status badge
- Node status badge
- Last agent heartbeat
- Last node heartbeat
- Capabilities
- MCP profiles
- Offline reason

**Step 4: Run frontend checks**

Use the project’s existing frontend test/lint command. If unknown, inspect `web/package.json` first.

**Step 5: Commit**

```bash
git add web/src/hooks/queries/useAgents.ts web/src/types/entities.ts web/src/routes/_authed/agents/index.tsx
git commit -m "feat(dashboard): distinguish node and agent presence"
```

---

## Phase 7: Security and Audit

### Task 12: Add secret redaction tests for ACN/task outputs

**Objective:** Ensure operational output never leaks credentials.

**Files:**
- Add/modify tests under `tests/unit/`
- Modify redaction helper if one exists; otherwise create a small shared helper

**Patterns to redact:**
- `Bearer ...`
- `token=...`
- `api_key=...`
- `password=...`
- `secret=...`
- GitHub PAT-like values
- OpenAI-style `sk-...` values

**Step 1: Search existing redaction helpers**

Use `search_files` before adding a new helper. Do not duplicate if one exists.

**Step 2: Add tests**

**Step 3: Implement/harden helper**

**Step 4: Verify**

```bash
pytest tests/unit -q -k "redact or secret or acn"
```

**Step 5: Commit**

```bash
git add app tests
git commit -m "fix(security): redact secrets from agent outputs"
```

---

### Task 13: Add minimal audit events

**Objective:** Make registry and task operations traceable.

**Events:**
- agent connected
- node heartbeat
- agent heartbeat
- task created
- task claimed
- task completed
- task failed
- heartbeat stale
- key rejected

**Files:**
- Add audit repository/table if missing
- Add tests
- Add audit writes at service layer

**Step 1: Inspect existing audit/logging model**

Search for `audit`, `event`, `activity`, and `log` in `app/`.

**Step 2: Add minimal table/repository if needed**

Keep fields simple:

```json
{
  "event_id": "...",
  "event_type": "agent_heartbeat",
  "agent_id": "...",
  "node_id": "...",
  "metadata": {},
  "created_at": "..."
}
```

**Step 3: Add service-level writes**

Prefer service layer over route layer to avoid duplicate audit logic.

**Step 4: Verify**

```bash
pytest tests/unit -q -k "audit or acn or tasks"
```

**Step 5: Commit**

```bash
git add app database/migrations tests
git commit -m "feat(acn): add audit events for agent operations"
```

---

## Live Rollout Plan

### Rollout 1: Presence-only hardening

Deploy only:
- presence schema
- heartbeat TTL classification
- dashboard distinction

Verify:

```bash
curl -sS https://hub.brunhilde.cloud/v1/health/simple
curl -sS https://hub.brunhilde.cloud/v1/acn/status
```

Expected:
- `brunhilde` online if its bridge is heartbeating
- `claude-code` offline unless a real claude-code bridge connects
- node `brunhilde-vps` may be online independently

### Rollout 2: Bridge identity hardening

Deploy only after Rollout 1 is stable.

Verify:
- run bridge process list
- confirm only intended agent identity heartbeats
- confirm stale records stay offline

### Rollout 3: Task queue dry-run

Deploy task API and bridge polling with dry-run executor first.

Verify:
- create task
- agent claims task
- agent returns dry-run result
- task cannot be double-claimed

### Rollout 4: MCP profile visibility

Deploy registry-safe MCP profile names only.

Verify:
- status includes profile names
- no secrets appear in API output
- actual MCP config stays local to node/Hermes

---

## Verification Checklist

Before considering this project complete:

- [ ] Node heartbeat never marks all mapped agents online.
- [ ] Agent heartbeat only refreshes authenticated agent.
- [ ] Stale agent remains offline even if node is online.
- [ ] `/v1/acn/status` distinguishes node vs agent status.
- [ ] Dashboard explains why an agent is offline.
- [ ] API key metadata contains no secret material.
- [ ] Capabilities are normalized.
- [ ] Agent task queue supports create/poll/claim/complete/fail.
- [ ] Claim is atomic enough to prevent double execution.
- [ ] MCP profile names are visible without leaking credentials.
- [ ] Secret redaction tests pass.
- [ ] Live curl verification passes after restart.

---

## Recommended First Implementation Slice

Start with **Milestone A: Truthful Agent Registry** only.

Scope:
1. Phase 1 Task 1
2. Phase 1 Task 2
3. Phase 6 Task 11, only the presence UI portion

Do **not** start task routing or MCP until this is stable.

**Milestone A done means:**
- `brunhilde` can be online.
- `claude-code` remains offline unless its own bridge is running.
- Dashboard visibly distinguishes node and agent presence.
- Tests prove the behavior.

---

## Notes for Future Implementer

- Current focused fix already changed `RemoteAgentService.heartbeat_node` so it no longer fans out online status to all mapped agents.
- Preserve that invariant.
- Existing modified frontend files may include prior dashboard work; inspect before editing and do not overwrite unrelated changes.
- Never print Turso auth token, ACN admin key, API keys, or MCP credentials in logs, plans, or chat.

## Implementation Notes — 2026-05-13

- Registry presence is truthful: node status and agent status are represented separately. Node heartbeat does not imply agent online.
- Agent heartbeat TTL is 300 seconds. Stale agent heartbeat yields agent_status=offline with offline_reason=stale_agent_heartbeat.
- API key metadata is the authoritative bridge identity source for task claim/start/complete/fail and task polling. Legacy agent_id query is allowed only when metadata is absent.
- Bridge runs in dry-run mode by default and only executes handlers with --execute.
- Capabilities, communication channels, skills, languages, and MCP profile names are normalized as safe string-list metadata; MCP remains a tool-layer hint, not a presence source.
- ACN task/heartbeat audit events are structured logs with recursive redaction of secret-like fields.
- Secrets such as API keys, tokens, passwords, and bearer credentials must stay node-local and must not be stored in registry metadata.
