---
phase: 03-vector-database
plan: 01
subsystem: foundation
tags: [migration, alembic, vector, config, tests, scaffolding]
requires:
  - alembic 1.12.1 toolchain (already present)
  - app.config.Settings (already present)
provides:
  - alembic revision 0003 (vector columns + DiskANN index)
  - app.database.vector_availability.is_vector_enabled
  - app.database.vector_availability.require_vector
  - pytest 'turso' marker
  - mock_embedding_backend fixture
  - 10 wave-0 test files
affects:
  - shared_memory, tasks, artifacts, messages tables (5 new columns each)
  - app/main.py lifespan (no longer mkdir zvec_path)
  - app/api/routes_health.py (no longer reports zvec_dir)
tech_stack:
  added: []
  removed:
    - zvec==0.1.0
  patterns:
    - alembic ALTER TABLE with try/except for idempotent ADD COLUMN
    - libsql_vector_idx CREATE INDEX guarded for plain SQLite
    - Settings.vector_search_enabled = None (auto) | True | False (override)
    - RFC 7807 problem detail for 503 vector unavailability
key_files:
  created:
    - alembic/versions/0003_vector_columns.py
    - app/database/vector_availability.py
    - tests/unit/test_vector_migration.py
    - tests/unit/test_vector_deps.py
    - tests/unit/test_vector_feature_flag.py
    - tests/unit/test_embedding_service.py
    - tests/unit/test_auto_index.py
    - tests/unit/test_retry_worker.py
    - tests/integration/test_vector_storage.py
    - tests/integration/test_auto_indexing.py
    - tests/integration/test_vector_search.py
    - tests/integration/test_search_api.py
  modified:
    - app/config.py
    - requirements.txt
    - pyproject.toml
    - tests/conftest.py
    - app/main.py
    - app/api/routes_health.py
decisions:
  - "Migration 0003 uses raw op.execute ALTER TABLE wrapped in try/except OperationalError to stay idempotent; SQLite has no IF NOT EXISTS for ADD COLUMN."
  - "DiskANN CREATE INDEX is wrapped in the same safe_execute helper so plain SQLite logs and skips, while Turso runs the real index."
  - "is_vector_enabled() honours an explicit Settings.vector_search_enabled override but cannot force-enable without a real Turso connection."
  - "test_search_api.py mounts a tiny FastAPI app inline so Plan 01 can validate require_vector behavior end to end without waiting for the real /v1/search route in Plan 06."
metrics:
  duration: 6m
  completed: 2026-04-13T06:42:50Z
  tasks: 2
  files_created: 12
  files_modified: 6
  commits: 3
---

# Phase 03 Plan 01: Foundation Summary

Lay the Phase 3 foundation: Alembic migration 0003 adds embedding columns and DiskANN indexes, the zvec placeholder is purged from runtime and config, app/database/vector_availability.py provides the single is_vector_enabled / require_vector contract used by every downstream plan, and 10 Wave 0 test files are scaffolded so Plans 02-06 can write against existing test modules.

## What Was Done

### Task 1 - Migration, config, dependency cleanup, vector_availability (TDD)

- **alembic/versions/0003_vector_columns.py** (revision 0003, down_revision 0002):
  - Constant `VEC_DIM = 384` matches sentence-transformers/all-MiniLM-L6-v2 (D-01).
  - Loops over `["shared_memory", "tasks", "artifacts", "messages"]` and runs five ALTER TABLE statements per table:
    - `embedding F32_BLOB(384)`
    - `embedding_model TEXT`
    - `embedding_status TEXT`
    - `embedding_error TEXT`
    - `embedded_at TIMESTAMP`
  - Each ALTER is wrapped in `_safe_execute` with `ignore_substrings=("duplicate column name",)` for idempotency.
  - Second loop creates one DiskANN index per table via `CREATE INDEX IF NOT EXISTS idx_{t}_embedding ON {t}(libsql_vector_idx(embedding, 'metric=cosine'))`. Wrapped in `_safe_execute` with `ignore_substrings=("no such function","libsql_vector_idx","syntax error","unknown function")` so plain SQLite logs a `vector_migration_skip` warning and continues; Turso creates the real index.
  - `downgrade()` drops the four indexes via `DROP INDEX IF EXISTS`. Columns intentionally left in place because SQLite cannot DROP COLUMN safely before 3.35.

- **app/config.py** Settings:
  - Removed `zvec_path` field entirely.
  - Added `embedding_provider: str = "local"` (env: `AGENTHUB_EMBEDDING_PROVIDER`).
  - Added `openai_api_key: Optional[str] = None` (env: `AGENTHUB_OPENAI_API_KEY`).
  - Added `vector_search_enabled: Optional[bool] = None` (env: `AGENTHUB_VECTOR_SEARCH_ENABLED`, where `None` means auto-detect from Turso configuration).

- **requirements.txt**: removed `zvec==0.1.0`. No new packages added in Wave 1; Plan 03 will introduce sentence-transformers / openai when the embedding service module lands.

- **app/database/vector_availability.py**: new module exposing `is_vector_enabled()` and `require_vector()`. Logic:
  - Explicit `vector_search_enabled=False` always disables.
  - Explicit `True` requires Turso to actually be configured (cannot force-enable).
  - `None` is auto: enabled iff `Database._use_turso` is true.
  - `require_vector()` raises `HTTPException(status_code=503)` with an RFC 7807 problem detail body that explains how to set `AGENTHUB_TURSO_DATABASE_URL` and `AGENTHUB_TURSO_AUTH_TOKEN`.

- **TDD tests** (RED -> GREEN):
  - `tests/unit/test_vector_migration.py` — 3 tests: columns added on all 4 tables, idempotent re-run, index skipped on SQLite. The fixture monkeypatches `AGENTHUB_DB_PATH` and resets `app.config.settings` because `alembic/env.py` overrides `sqlalchemy.url` from settings, not from the Config's main option.
  - `tests/unit/test_vector_deps.py` — 2 tests: requirements.txt has no zvec line, Settings has no zvec_path attribute.
  - `tests/unit/test_vector_feature_flag.py` — 5 tests covering all four flag states + the explicit-true-without-Turso edge case.

### Task 2 - Wave 0 test scaffolds, turso marker, residual zvec cleanup

- **pyproject.toml**: added `markers = ["turso: requires live Turso DB for vector tests"]` under `[tool.pytest.ini_options]`.
- **tests/conftest.py**:
  - `pytest_configure(config)` registers the marker (defensive duplicate of pyproject so external runners pick it up).
  - `pytest_collection_modifyitems(config, items)` auto-skips any item carrying the `turso` keyword unless both `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` are set (Approach A, mark-and-skip per 03-RESEARCH.md).
  - `mock_embedding_backend` fixture: function-scoped helper returning a `_MockEmbeddingBackend` with `dim=384`, `model_name="mock"`, and an async `embed(texts)` method producing deterministic vectors.

- **7 stub test files** + the mounted-app stub for the search API:
  - `tests/unit/test_embedding_service.py` — 5 xfail stubs ("Plan 03 implements")
  - `tests/unit/test_auto_index.py` — 2 xfail stubs ("Plan 04 implements")
  - `tests/unit/test_retry_worker.py` — 1 xfail stub ("Plan 04 implements")
  - `tests/integration/test_vector_storage.py` — pytestmark = pytest.mark.turso, 1 xfail stub ("Plan 02 implements")
  - `tests/integration/test_vector_search.py` — pytestmark = pytest.mark.turso, 3 xfail stubs ("Plan 02/05 implements")
  - `tests/integration/test_auto_indexing.py` — 1 xfail stub ("Plan 04 implements")
  - `tests/integration/test_search_api.py` — 5 tests: `test_503_local` and `test_flag_off` PASS now (mount a tiny FastAPI app with `Depends(require_vector)` and assert the 503 problem); the other 3 are xfail for Plans 05/06.

- **Residual zvec cleanup (Rule 3 - blocking)**: the integration test suite started crashing in conftest because `app/main.py` lifespan and `app/api/routes_health.py` still referenced `settings.zvec_path`. Both were updated to drop the zvec mkdir and the `zvec_dir` health field.

## Verification

```bash
.venv/bin/python -m pytest tests/ --no-cov -m "not turso"
# 60 passed, 1 skipped, 4 deselected, 12 xfailed

.venv/bin/python -m pytest -m turso --collect-only --no-cov
# 4/77 tests collected (73 deselected) - all turso tests are skipped because no creds

AGENTHUB_DB_PATH=/tmp/fresh.db AGENTHUB_ADMIN_USER=x AGENTHUB_ADMIN_PASSWORD=y \
  .venv/bin/alembic upgrade head
# Migration runs, 4 vector_migration_skip warnings for the indexes (expected on SQLite)

AGENTHUB_ADMIN_USER=x AGENTHUB_ADMIN_PASSWORD=y \
  .venv/bin/python -c "from app.main import app; print('app ok')"
# app ok

.venv/bin/pip check | grep -i zvec
# (no output - zvec is gone)
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Residual zvec_path references in app code**
- **Found during:** Task 2 (full suite verification)
- **Issue:** Removing `Settings.zvec_path` made `app/main.py` lifespan and `app/api/routes_health.py` raise `AttributeError` at import time, which broke every integration test in conftest.
- **Fix:** Removed `os.makedirs(settings.zvec_path, ...)` from `app/main.py` lifespan and the `zvec_dir` block from `routes_health.py` storage health.
- **Files modified:** app/main.py, app/api/routes_health.py
- **Commit:** 6a82762

**2. [Rule 3 - Blocking] alembic env.py overrides sqlalchemy.url from Settings**
- **Found during:** Task 1 GREEN phase (migration tests failed because tables were empty)
- **Issue:** The original test fixture set `cfg.set_main_option("sqlalchemy.url", ...)`, but `alembic/env.py` later does `config.set_main_option("sqlalchemy.url", f"sqlite:///{settings.db_path}")` and wins. Migrations were running against the conftest temp DB instead of the test's isolated one.
- **Fix:** Updated `temp_sqlite_db` fixture to monkeypatch `AGENTHUB_DB_PATH` and reset `app.config.settings = Settings()` so env.py picks up the new path.
- **Files modified:** tests/unit/test_vector_migration.py
- **Commit:** f92bcdc

## Known Gotchas For Downstream Plans

- **Idempotency strategy:** Future plans that touch the same tables should follow the same `_safe_execute(..., ignore_substrings=("duplicate column name",))` pattern. Do NOT use IF NOT EXISTS — SQLite does not support it for ALTER TABLE ADD COLUMN.
- **`is_vector_enabled()` is the single source of truth:** Plans 02-06 must call it (or `require_vector`) instead of inspecting `Database._use_turso` directly.
- **Mock embedding backend dim is 384:** Tests that need a different dim should subclass `_MockEmbeddingBackend` rather than mutate it.
- **F32_BLOB on SQLite is parsed as BLOB:** the column exists and accepts bytes, but no vector functions work without Turso. This is by design (D-08) - vector endpoints return 503 on local SQLite.
- **`test_search_api.py::test_503_local` mounts its own tiny FastAPI app**, not the production one. When Plan 06 wires the real `/v1/search` route, those two tests should switch to the real `app` from `app.main` and the existing assertions should keep passing.

## Self-Check: PASSED

- alembic/versions/0003_vector_columns.py: FOUND
- app/database/vector_availability.py: FOUND
- tests/unit/test_vector_migration.py: FOUND
- tests/unit/test_vector_deps.py: FOUND
- tests/unit/test_vector_feature_flag.py: FOUND
- tests/unit/test_embedding_service.py: FOUND
- tests/unit/test_auto_index.py: FOUND
- tests/unit/test_retry_worker.py: FOUND
- tests/integration/test_vector_storage.py: FOUND
- tests/integration/test_auto_indexing.py: FOUND
- tests/integration/test_vector_search.py: FOUND
- tests/integration/test_search_api.py: FOUND
- Commit 8721454 (RED test scaffolds): FOUND
- Commit f92bcdc (Task 1 GREEN): FOUND
- Commit 6a82762 (Task 2): FOUND
