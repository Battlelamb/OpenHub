---
phase: 09
name: ANP Compatibility Spike
status: in_progress
wave: anp-compatibility
created: 2026-05-31
updated: 2026-05-31T11:45:54Z
owner: OpenHub GSD
---

# Phase 09 — ANP Compatibility Spike Implementation Plan

> **For Hermes:** Use `openhub-operations`, `openhub-competitive-methods`, `writing-plans`, and `test-driven-development` to implement this plan task-by-task. Use repo-local GSD validation before every commit.

**Goal:** Expose a public-safe Agent Network Protocol (ANP) compatibility surface for OpenHub agents without changing OpenHub’s authoritative trust, task, evidence, or review-gate model.

**Architecture:** Add a small read-only compatibility layer that serializes explicitly public OpenHub agents into ANP-style JSON-LD Agent Description documents and exposes a `.well-known/agent-descriptions` discovery document. Keep the mapping in a service/model module, keep routes thin, default discovery to private/empty unless an agent opts in, and prove no secrets or private metadata leak.

**Tech Stack:** FastAPI, Pydantic, existing OpenHub `AgentRepository`/`AgentService`, pytest `TestClient`, existing GSD verification tools.

---

## Background

ANP (`agent-network-protocol/AgentNetworkProtocol`) defines:

- Agent Description Protocol (ADP): JSON/JSON-LD agent profile documents.
- Agent Discovery Protocol (ADSP): active discovery at `https://{domain}/.well-known/agent-descriptions` returning a JSON-LD `CollectionPage`.
- `did:wba` identity and meta-protocol negotiation as deeper/draft layers.

OpenHub should adopt the public discovery/description surface first. Do **not** replace OpenHub ACN identity, `inv_...` invites, `oh_...` per-agent keys, admin keys, task routing, evidence bundles, or human review gates.

Reference note captured in Obsidian:

- `/home/brunhilde/Documents/Obsidian Vault/Agent Network Protocol (ANP).md`

## Success criteria

1. OpenHub serves `GET /.well-known/agent-descriptions` publicly.
2. OpenHub serves per-agent ANP-style description documents for explicitly public agents only.
3. Private/default agents are excluded from discovery and return 404 from public ANP description endpoints.
4. Public description JSON-LD includes only safe fields: agent name, public description, capabilities, public interface hints, optional DID if explicitly present, and no API keys/tokens/admin metadata/IP/workspace secrets.
5. Pagination works for discovery.
6. Tests cover schema shape, public/private filtering, pagination, base URL generation, and secret redaction/no-leak behavior.
7. Docs mark ANP compatibility as experimental and explain that `did:wba` is not yet OpenHub’s production auth layer.
8. GSD health/consistency and focused tests pass before commit/push.

## Non-goals

- No `did:wba` key generation or verification in this phase.
- No E2EE messaging implementation.
- No passive registration with external ANP search services.
- No replacement of ACN invite/API-key auth.
- No dashboard UX unless a tiny docs/navigation link is needed later.
- No publishing/release/tag action as part of this phase.

## Public/private policy

Default is private.

An agent is public-discoverable only if one of these is true:

- `agent.labels["anp_public"] == "true"`
- `agent.metadata["anp_public"] is True`
- `agent.metadata["public"] is True`

Everything else is excluded.

Sensitive metadata denylist:

- keys containing `key`, `token`, `secret`, `password`, `credential`, `auth`, `bearer`, `cookie`, `session`
- IP/network/workstation details: `ip_address`, `hostname`, `workspace_path`, `os_info`
- callback URLs unless explicitly marked public-safe
- raw labels/metadata are never returned wholesale

## Proposed endpoint contract

### `GET /.well-known/agent-descriptions`

Query params:

- `page: int = 1`, minimum 1
- `page_size: int = 50`, minimum 1, maximum 100

Response shape:

```json
{
  "@context": {
    "@vocab": "https://schema.org/",
    "ad": "https://agent-network-protocol.com/ad#"
  },
  "@type": "CollectionPage",
  "url": "https://hub.example/.well-known/agent-descriptions?page=1&page_size=50",
  "items": [
    {
      "@type": "ad:AgentDescription",
      "name": "brunhilde",
      "@id": "https://hub.example/v1/anp/agents/{agent_id}/ad.json"
    }
  ],
  "next": "https://hub.example/.well-known/agent-descriptions?page=2&page_size=50"
}
```

`next` is omitted when there is no next page.

### `GET /v1/anp/agents/{agent_id}/ad.json`

Response shape:

```json
{
  "@context": {
    "@vocab": "https://schema.org/",
    "ad": "https://agent-network-protocol.com/ad#",
    "openhub": "https://hub.brunhilde.cloud/ns/openhub#"
  },
  "@type": "ad:AgentDescription",
  "@id": "https://hub.example/v1/anp/agents/{agent_id}/ad.json",
  "name": "brunhilde",
  "description": "Public agent description",
  "version": "experimental-openhub-anp-v0",
  "openhub:agentId": "{agent_id}",
  "openhub:status": "online",
  "knowsAbout": ["research", "code_edit"],
  "ad:interfaces": [
    {
      "@type": "ad:NaturalLanguageInterface",
      "protocol": "OpenHub",
      "description": "Use OpenHub ACN/API-key authenticated task routing for private operations."
    }
  ],
  "ad:securityDefinitions": {
    "openhub_api_key": {
      "scheme": "openhub-api-key",
      "in": "header",
      "name": "X-API-Key"
    }
  },
  "ad:security": "openhub_api_key"
}
```

Only include `did` if `agent.metadata["did"]` or `agent.metadata["did_wba"]` is explicitly present.

## Task breakdown

### Task 09-01: Record the ANP mapping design

**Objective:** Document the exact OpenHub → ANP mapping and security policy before code.

**Files:**

- Create: `docs/ANP_COMPATIBILITY.md`
- Create evidence: `.planning/phases/09-anp-compatibility/09-01-ANP-MAPPING-DESIGN.md`

**Steps:**

1. Write `docs/ANP_COMPATIBILITY.md` with:
   - scope: experimental read-only compatibility
   - endpoints
   - public/private opt-in policy
   - field mapping table
   - sensitive metadata denylist
   - non-goals for `did:wba`, E2EE, passive registration
2. Add evidence file summarizing design decisions and the ANP repo source inspected.
3. Run:
   - `python scripts/check_dependency_drift.py`
   - `node .codex/get-shit-done/bin/gsd-tools.cjs validate health`
   - `node .codex/get-shit-done/bin/gsd-tools.cjs validate consistency`
4. Commit:
   - `docs: plan ANP compatibility surface`

**Acceptance:** Human/operator can read one doc and understand exactly what will be exposed publicly.

---

### Task 09-02: Add ANP Pydantic models and serializer service

**Objective:** Convert an `Agent` model into safe ANP JSON-LD without adding routes yet.

**Files:**

- Create: `app/models/anp.py`
- Create: `app/services/anp_compatibility_service.py`
- Create: `tests/unit/test_anp_compatibility_service.py`

**Step 1: Write failing tests**

Test cases:

- `test_public_flag_accepts_anp_public_label`
- `test_public_flag_accepts_metadata_boolean`
- `test_private_agent_is_not_public_by_default`
- `test_agent_description_omits_sensitive_metadata`
- `test_agent_description_includes_did_only_when_explicit`
- `test_discovery_page_paginates_public_agents`

Use direct `Agent(...)` objects; do not touch the database for serializer tests.

**Step 2: Run failing tests**

Run:

```bash
python -m pytest tests/unit/test_anp_compatibility_service.py -q --tb=short
```

Expected: fail because the module does not exist.

**Step 3: Implement minimal models/service**

Create model types or typed dict helpers for:

- `ANP_CONTEXT`
- `ANPCollectionPage`
- `ANPAgentDescription`
- `ANPAgentDescriptionItem`

Create service functions:

- `is_anp_public(agent: Agent) -> bool`
- `build_agent_description(agent: Agent, base_url: str) -> dict`
- `build_discovery_page(agents: list[Agent], base_url: str, page: int, page_size: int) -> dict`

Keep service pure and deterministic.

**Step 4: Verify pass**

Run:

```bash
python -m pytest tests/unit/test_anp_compatibility_service.py -q --tb=short
```

Expected: pass.

**Step 5: Commit**

```bash
git add app/models/anp.py app/services/anp_compatibility_service.py tests/unit/test_anp_compatibility_service.py
git commit -m "feat: add ANP compatibility serializer"
```

---

### Task 09-03: Add public per-agent ADP endpoint

**Objective:** Expose `GET /v1/anp/agents/{agent_id}/ad.json` for public agents only.

**Files:**

- Create: `app/api/routes_anp.py`
- Modify: `app/main.py` to include the router before the dashboard catch-all section
- Create: `tests/unit/test_anp_routes.py`
- Create evidence: `.planning/phases/09-anp-compatibility/09-03-ADP-ENDPOINT.md`

**Step 1: Write failing route tests**

Tests:

- request for public agent returns `200` and JSON-LD fields
- request for private agent returns `404`
- request for missing agent returns `404`
- response does not contain values such as `oh_`, `ak_`, `Bearer`, `secret`, `workspace_path`, `ip_address`

Prefer monkeypatching `get_database` or the route dependency if this is lighter than full DB setup. If using the repository, create disposable test rows only in the isolated test DB.

**Step 2: Run failing tests**

```bash
python -m pytest tests/unit/test_anp_routes.py -q --tb=short
```

Expected: fail because route does not exist.

**Step 3: Implement route**

In `app/api/routes_anp.py`:

- `router = APIRouter(tags=["anp [experimental]"])`
- dependency creates `AgentRepository(get_database())`
- endpoint gets agent by ID
- returns 404 when missing or not public
- builds base URL from `request.base_url`
- returns serializer output

**Step 4: Include router**

In `app/main.py`:

- import `routes_anp.router as anp_router`
- `app.include_router(anp_router)` near other API routers, before static dashboard mounting

**Step 5: Verify pass**

```bash
python -m pytest tests/unit/test_anp_routes.py tests/unit/test_static_mount.py -q --tb=short
```

Expected: pass.

**Step 6: Commit**

```bash
git add app/api/routes_anp.py app/main.py tests/unit/test_anp_routes.py .planning/phases/09-anp-compatibility/09-03-ADP-ENDPOINT.md
git commit -m "feat: expose public ANP agent descriptions"
```

---

### Task 09-04: Add `.well-known/agent-descriptions` discovery endpoint

**Objective:** Expose public ANP discovery with pagination.

**Files:**

- Modify: `app/api/routes_anp.py`
- Modify: `tests/unit/test_anp_routes.py`
- Create evidence: `.planning/phases/09-anp-compatibility/09-04-WELL-KNOWN-DISCOVERY.md`

**Step 1: Write failing tests**

Tests:

- `GET /.well-known/agent-descriptions` returns `CollectionPage`
- includes only public agents
- supports `page` and `page_size`
- includes `next` only when more public agents exist
- clamps/rejects invalid page params with FastAPI validation
- generated item `@id` points at `/v1/anp/agents/{agent_id}/ad.json`

**Step 2: Run failing tests**

```bash
python -m pytest tests/unit/test_anp_routes.py -q --tb=short
```

Expected: fail for missing discovery endpoint.

**Step 3: Implement endpoint**

In `routes_anp.py`:

- `@router.get("/.well-known/agent-descriptions", include_in_schema=False)` or a second router with no prefix.
- Load agents from repository.
- Filter through `is_anp_public` before pagination.
- Return `build_discovery_page(...)`.

If `AgentRepository` lacks a direct `list_all()` method from `BaseRepository`, inspect `BaseRepository` and use the existing safe list method. Do not write raw SQL unless repository support is insufficient.

**Step 4: Verify pass**

```bash
python -m pytest tests/unit/test_anp_compatibility_service.py tests/unit/test_anp_routes.py -q --tb=short
```

Expected: pass.

**Step 5: Commit**

```bash
git add app/api/routes_anp.py tests/unit/test_anp_routes.py .planning/phases/09-anp-compatibility/09-04-WELL-KNOWN-DISCOVERY.md
git commit -m "feat: add ANP well-known discovery"
```

---

### Task 09-05: Public smoke, docs, and phase closeout

**Objective:** Prove the feature locally, document it, update planning truth, and push.

**Files:**

- Modify: `README.md`
- Modify: `docs/ANP_COMPATIBILITY.md`
- Modify: `.planning/STATE.md`
- Modify: `.planning/ROADMAP.md`
- Modify: `.planning/HANDOFF.json`
- Create: `.planning/phases/09-anp-compatibility/09-SUMMARY.md`
- Create evidence: `.planning/phases/09-anp-compatibility/09-05-VERIFICATION.md`

**Verification commands:**

```bash
python -m pytest tests/unit/test_anp_compatibility_service.py tests/unit/test_anp_routes.py -q --tb=short
python -m pytest tests/unit/test_static_mount.py tests/unit/test_acn_redaction.py -q --tb=short
python scripts/check_dependency_drift.py
node .codex/get-shit-done/bin/gsd-tools.cjs validate health
node .codex/get-shit-done/bin/gsd-tools.cjs validate consistency
git diff --check
git status --short --branch
```

After commit/push, verify remote truth:

```bash
git rev-parse HEAD
git rev-parse origin/master
git ls-remote origin refs/heads/master
```

If deployment/live smoke is in scope for the implementation pass, verify public endpoint after deploy/restart:

```bash
curl -sS https://hub.brunhilde.cloud/.well-known/agent-descriptions | python -m json.tool
```

Expected live behavior may be an empty `items` list if no agents have opted into `anp_public`.

**Commit:**

```bash
git add README.md docs/ANP_COMPATIBILITY.md .planning/STATE.md .planning/ROADMAP.md .planning/HANDOFF.json .planning/phases/09-anp-compatibility/
git commit -m "docs: close ANP compatibility spike"
git push origin master
```

---

## Implementation order

1. Design doc first.
2. Pure serializer tests/service.
3. Per-agent public description route.
4. Well-known discovery route.
5. Docs, smoke, GSD closeout, commit/push.

## Risk controls

- Default private: no public discovery unless explicitly opted in.
- No secrets: never return raw metadata or labels wholesale.
- No auth-model replacement: ANP advertises OpenHub auth, it does not replace it.
- No fake DID claims: include DID only if explicitly provided.
- Focused tests before broad tests.
- Commit after each working slice.

## Open questions for implementation

These should be answered by code inspection during Task 09-02/09-03, not guessed:

1. Whether `AgentRepository.list_all()` is available through `BaseRepository`; if not, add a narrow repository helper with tests.
2. Whether `request.base_url` is enough behind Cloudflare, or whether a later `AGENTHUB_PUBLIC_BASE_URL` setting is needed.
3. Whether public opt-in should eventually be editable from dashboard Settings/Agents; not required for this spike.

## Ready-to-execute command

When implementation begins, start with:

```bash
cd /home/brunhilde/OpenHub
python -m pytest tests/unit/test_anp_compatibility_service.py -q --tb=short
```

Expected first result: failure because the test file does not exist yet. Then create Task 09-02’s failing tests.
