---
phase: 03
slug: vector-database
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-12
---

# Phase 03 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 with pytest-asyncio 0.21.1 |
| **Config file** | pyproject.toml |
| **Quick run command** | `.venv/bin/python -m pytest tests/ -x -q --tb=short --no-cov -m "not turso"` |
| **Full suite command** | `.venv/bin/python -m pytest tests/ -v --tb=short --no-cov` |
| **Turso-only tests** | `TURSO_DATABASE_URL=... TURSO_AUTH_TOKEN=... .venv/bin/python -m pytest tests/ -m turso -v` |
| **Estimated runtime** | ~2 seconds (non-turso), ~10 seconds (full with turso) |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/ -x -q --tb=short -m "not turso"`
- **After every plan wave:** Run `.venv/bin/python -m pytest tests/ -v --tb=short -m "not turso"`
- **Before `/gsd:verify-work`:** Full non-turso suite must be green; turso suite must pass in CI with credentials
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 03-01-01 | 01 | 1 | VEC-01 | migration | `.venv/bin/python -m pytest tests/unit/test_vector_migration.py -v` | pending |
| 03-02-01 | 02 | 2 | VEC-01,02 | turso | `.venv/bin/python -m pytest tests/integration/test_vector_storage.py -v -m turso` | pending |
| 03-03-01 | 03 | 2 | D-01,D-04 | unit | `.venv/bin/python -m pytest tests/unit/test_embedding_service.py -v` | pending |
| 03-04-01 | 04 | 3 | VEC-04 | integration | `.venv/bin/python -m pytest tests/integration/test_auto_indexing.py -v` | pending |
| 03-05-01 | 05 | 3 | VEC-02,05 | integration | `.venv/bin/python -m pytest tests/integration/test_vector_search.py -v` | pending |
| 03-06-01 | 06 | 4 | VEC-06 | unit | `.venv/bin/python -m pytest tests/unit/test_vector_feature_flag.py -v` | pending |

*Status: pending - awaiting planning*

---

## Wave 0 Requirements

- [ ] Add `pytest.mark.turso` marker registration to pyproject.toml
- [ ] Create `tests/unit/test_vector_migration.py` - stub for Alembic DDL verification
- [ ] Create `tests/integration/test_vector_storage.py` - stub for Turso smoke test (marked @pytest.mark.turso)
- [ ] Create `tests/unit/test_embedding_service.py` - stub for local/OpenAI backend tests
- [ ] Create `tests/integration/test_auto_indexing.py` - stub for BackgroundTasks verification
- [ ] Create `tests/integration/test_vector_search.py` - stub for /v1/search endpoint tests
- [ ] Create `tests/unit/test_vector_feature_flag.py` - stub for 503 fallback tests
- [ ] Add mock backend fixture in conftest.py for embedding service unit tests

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| DiskANN index actually speeds up queries | VEC-03 | Requires large dataset (>10k rows) | Insert 10k rows, benchmark EXPLAIN QUERY PLAN with and without index |
| First-time sentence-transformers model download | D-01 | Downloads ~80MB from HuggingFace | Clean install, first call, verify model cached in ~/.cache/huggingface |
| Turso F32_BLOB parameter binding smoke test | CRITICAL | Research flagged MEDIUM confidence | Plan 02 Task 1 must run `vector32(json.dumps(...))` against real Turso and verify round-trip |
| OpenAI embeddings work with real API | D-01 | Requires valid API key | Set `AGENTHUB_OPENAI_API_KEY`, `AGENTHUB_EMBEDDING_PROVIDER=openai`, verify embedding dimensions match 1536 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] Turso-only tests properly marked and skipped when credentials absent
- [ ] Feedback latency < 15s for non-turso subset
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
