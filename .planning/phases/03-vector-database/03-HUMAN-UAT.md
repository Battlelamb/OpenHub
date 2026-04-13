---
status: partial
phase: 03-vector-database
source: [03-VERIFICATION.md]
started: 2026-04-13T00:00:00Z
updated: 2026-04-13T00:00:00Z
---

## Current Test

[awaiting human testing — all items require a live Turso database]

## Tests

### 1. Turso vector binding smoke test
expected: `scripts/smoke_turso_vector.py` run against a real Turso DB exits 0 and confirms `vector32(json.dumps(vec))` binding works end-to-end (insert + retrieve 384-dim vector).
result: [pending]

### 2. End-to-end semantic search (SC-1)
expected: With a live Turso DB + embeddings enabled, `POST /v1/search` with a natural-language query returns at least one hit ordered by cosine distance. Tests tagged `turso` in `tests/integration/test_vector_search.py::test_end_to_end_search` pass.
result: [pending]

### 3. Persistence across restart (SC-2)
expected: After writing memory/task/artifact/message rows with embeddings and running `docker compose restart`, F32_BLOB columns survive and `/v1/search` still returns the same hits.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
