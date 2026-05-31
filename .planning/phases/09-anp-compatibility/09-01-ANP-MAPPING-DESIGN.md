---
phase: 09
slice: 09-01
name: ANP mapping design
status: complete
updated: 2026-05-31T11:43:58Z
---

# 09-01 — ANP Mapping Design

## Objective

Document the exact OpenHub → ANP compatibility mapping and security policy before implementation.

## Files

- Created: `docs/ANP_COMPATIBILITY.md`
- Created: `.planning/phases/09-anp-compatibility/09-01-ANP-MAPPING-DESIGN.md`

## Source material

External ANP material was inspected before this slice:

- `agent-network-protocol/AgentNetworkProtocol`
- `07-anp-agent-description-protocol-specification.md`
- `08-ANP-Agent-Discovery-Protocol-Specification.md`
- `examples/adp/hotel/examples/ad.json`
- Obsidian note: `/home/brunhilde/Documents/Obsidian Vault/Agent Network Protocol (ANP).md`

## Design decisions

1. ANP is an experimental interoperability/discovery surface, not OpenHub's authority model.
2. OpenHub keeps ACN invite codes, per-agent keys, admin keys, task routing, evidence bundles, and human review gates as the source of truth.
3. Public discovery is opt-in only:
   - `agent.labels["anp_public"] == "true"`
   - `agent.metadata["anp_public"] is true`
   - `agent.metadata["public"] is true`
4. Private or missing agents return `404` from direct public description endpoints.
5. Public responses never return raw labels or metadata wholesale.
6. DID values are included only when explicitly present in safe metadata; OpenHub does not synthesize `did:wba` claims.
7. The first implementation should be dependency-free and use local JSON-LD dictionaries/Pydantic models rather than importing upstream protocol code.
8. `request.base_url` is acceptable for the initial spike; a future `AGENTHUB_PUBLIC_BASE_URL` can be added only if proxy behavior requires it.

## Endpoint contract captured

- `GET /.well-known/agent-descriptions`
  - ANP-style JSON-LD `CollectionPage`
  - `page` and `page_size` params
  - public agents only
  - optional `next`

- `GET /v1/anp/agents/{agent_id}/ad.json`
  - ANP-style Agent Description document
  - public agents only
  - safe OpenHub fields only
  - static OpenHub interface/security scheme names, never key values

## Sensitive data policy captured

The design doc denies keys containing these substrings:

- `key`
- `token`
- `secret`
- `password`
- `credential`
- `auth`
- `bearer`
- `cookie`
- `session`

It also denies machine/runtime details such as IP addresses, hostnames, workspace paths, OS info, local file paths, process IDs, raw environment names/values, and bridge command lines.

## Acceptance

A human/operator can now read `docs/ANP_COMPATIBILITY.md` and understand exactly what will be publicly exposed, which OpenHub fields map to ANP-style output, and which values must never appear in public responses.

## Verification

Local validation on 2026-05-31T11:45:54Z:

```text
.venv/bin/python scripts/check_dependency_drift.py
→ Dependency drift guard passed:
  - backend pins checked: 25
  - pyproject dependencies known: 29 (20 runtime)
  - frontend specs checked: 28 dependencies, 24 devDependencies

node .codex/get-shit-done/bin/gsd-tools.cjs validate health
→ healthy; 0 errors; 0 warnings; 1 info entry noting Phase 09 has a PLAN and no umbrella SUMMARY yet

node .codex/get-shit-done/bin/gsd-tools.cjs validate consistency
→ passed; 0 errors; 0 warnings

git diff --check
→ passed
```

The remaining GSD info entry is expected while Phase 09 is open.
