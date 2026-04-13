---
phase: 03-vector-database
plan: 06
subsystem: vector-search-beta-rollout
tags: [vector, beta, openapi, documentation, feature-flag, structlog, tdd]
requires:
  - app.database.vector_availability.is_vector_enabled (Plan 01)
  - app/api/routes_search.py (Plan 05)
  - app/main.py lifespan (Plan 04 retry worker)
provides:
  - app.main openapi_tags entry "search [experimental]" with BETA description
  - app.main lifespan vector_search_disabled / vector_search_enabled startup logs
  - README.md "Vector Search (Beta)" section
  - CHANGELOG.md Phase 3 entry listing VEC-01..VEC-06
  - .env.example documenting AGENTHUB_VECTOR_SEARCH_ENABLED, AGENTHUB_EMBEDDING_PROVIDER, AGENTHUB_OPENAI_API_KEY
  - 4 new flag combination tests covering all (Turso, flag) states
  - 4 new integration tests (OpenAPI tag description, /v1/search experimental marker, startup warning fired/not-fired)
affects:
  - app/main.py (FastAPI() openapi_tags arg + lifespan startup advisory)
  - app/api/routes_search.py (docstring referencing BETA contract)
  - tests/unit/test_vector_feature_flag.py (extended with 4 new combinations)
  - tests/integration/test_search_api.py (extended with 4 new BETA contract tests)
tech-stack:
  added: []
  removed: []
  patterns:
    - openapi_tags as the documented seam for marking experimental routers
    - structlog warning at startup as the user-visible signal for opt-in features
    - capsys-based test capture for structlog PrintLoggerFactory (caplog does not work)
    - bare URL wrapping in markdown to satisfy MD034
key-files:
  created:
    - CHANGELOG.md
    - .planning/phases/03-vector-database/03-06-SUMMARY.md
  modified:
    - app/main.py
    - app/api/routes_search.py
    - README.md
    - .env.example
    - tests/unit/test_vector_feature_flag.py
    - tests/integration/test_search_api.py
key-decisions:
  - "structlog uses PrintLoggerFactory writing to stdout, not stdlib logging - tests must use capsys, not caplog, to capture startup warnings."
  - "Removed AGENTHUB_ZVEC_PATH from .env.example because Settings.zvec_path was deleted in Plan 01 and the entry would now confuse OSS users."
  - "Wrapped Turso bare URL in README as [turso.tech](https://turso.tech) to satisfy MD034 lint."
  - "openapi_tags is added at the FastAPI() constructor in app/main.py so the BETA description applies app-wide; the routers themselves still use tags=['search [experimental]'] which links to the description by name."
requirements-completed: [VEC-06]

# Metrics
duration: 4m
completed: 2026-04-13
---

# Phase 03 Plan 06: VEC-06 Beta Opt-In Rollout Summary

VEC-06 is closed: Phase 3 ships as opt-in beta with a startup advisory log when vector search is unavailable, an OpenAPI BETA tag description on the "search [experimental]" router, README + CHANGELOG + .env.example documentation for OSS users, and full test coverage of all four (Turso, flag) combinations plus the BETA contract.

## Performance

- **Duration:** 4m
- **Started:** 2026-04-13T07:14:50Z
- **Completed:** 2026-04-13T07:18:59Z
- **Tasks:** 2
- **Files modified:** 6 (4 modified, 2 created)
- **Tests added:** 8 (4 unit flag + 2 OpenAPI + 2 startup warning)
- **Suite delta:** 127 -> 135 non-turso tests passing

## What Was Done

### Task 1 - Startup warning + OpenAPI BETA tag + flag test hardening (TDD)

**RED phase** (commit `dc1a019`):
- `tests/unit/test_vector_feature_flag.py` extended with 4 new tests covering all (Turso, flag) combinations:
  - `test_explicit_false_overrides_turso` (Turso=True, flag=False -> disabled)
  - `test_true_without_turso_still_false` (Turso=False, flag=True -> disabled)
  - `test_none_auto_detects_turso` (Turso=True, flag=None -> enabled)
  - `test_none_auto_detects_no_turso` (Turso=False, flag=None -> disabled)
  Two of these duplicate the existing Plan 01 coverage but with the explicit Plan 06 names so the BETA contract is documented at the test-name level. The other two are new combinations.
- `tests/integration/test_search_api.py` extended with 4 new tests:
  - `test_openapi_tag_has_description` - GET /openapi.json, asserts the top-level "search [experimental]" tag has a description containing BETA/beta/opt-in
  - `test_search_endpoint_marked_experimental_in_operation` - asserts /v1/search POST has an experimental tag in its operation tags
  - `test_startup_logs_warning_on_local_sqlite` - capsys-captures TestClient lifespan startup output and asserts vector_search_disabled appears
  - `test_startup_no_warning_when_enabled` - patches is_vector_enabled to True, asserts vector_search_disabled does NOT appear

  Initial RED run failed on the OpenAPI test (no description) and the startup-warning test (warning not wired). The 4 unit flag tests passed immediately because is_vector_enabled already had the right semantics from Plan 01; this was expected for the explicit-true and auto cases.

**GREEN phase** (commit `ee4a429`):
- `app/main.py`:
  - Added module-level `openapi_tags` list with one entry: `name="search [experimental]"`, `description="Semantic vector search ... BETA: opt-in feature ..."`. Passed to `FastAPI(..., openapi_tags=openapi_tags)`.
  - Lifespan startup, after the embedding retry worker block: `from .database.vector_availability import is_vector_enabled; if not is_vector_enabled(): logger.warning("vector_search_disabled", reason=..., hint=...) else: logger.info("vector_search_enabled")`. The hint string includes the env vars to set.
- `app/api/routes_search.py`: docstring updated to explicitly reference VEC-06 BETA contract and the matching tag description in app/main.py.

**Test capture pitfall** (recorded as a key decision):
The first cut of the startup-warning test used `caplog`, which captures stdlib logging records. OpenHub's structlog setup (`app/logging.py`) uses `structlog.PrintLoggerFactory()`, which writes directly to stdout instead of routing through stdlib logging. caplog stays empty. The fix was to switch to `capsys` and assert against `captured.out + captured.err`. Documented under Known Gotchas so downstream plans don't repeat the mistake.

### Task 2 - README, CHANGELOG, .env.example (commit `021c4fb`)

- **README.md**: new `## Vector Search (Beta)` section inserted after the Configuration section, before Tech Stack. Subsections: opening paragraph (states beta status, 503 fallback, startup log), Requirements, Setup (env block + alembic + curl verify), API (7 endpoints listed with request body shape), Limitations (5 bullets), Disabling.
- **CHANGELOG.md**: created file. Phase 3 entry lists all 6 VEC requirements, the zvec removal, the new settings, and the experimental OpenAPI tag. Beta status is marked in both the section header (`### Added (BETA / Experimental)`) and in the Notes section.
- **.env.example**: removed the dead `AGENTHUB_ZVEC_PATH` line (Settings.zvec_path was deleted in Plan 01). Added a `# Vector Search (Phase 3 Beta) - optional, requires Turso` block right above the existing `AGENTHUB_VECTOR_BATCH_SIZE` line, with three commented-out env vars: `AGENTHUB_VECTOR_SEARCH_ENABLED`, `AGENTHUB_EMBEDDING_PROVIDER`, `AGENTHUB_OPENAI_API_KEY`.
- **MD034 fix**: README initially had a bare URL `https://turso.tech`. The IDE flagged MD034/no-bare-urls so it was rewritten to `[turso.tech](https://turso.tech)`. Recorded as a key decision so future doc plans pre-wrap URLs.

## Final OpenAPI Tag Description

```
Semantic vector search over memories, tasks, artifacts, and messages.
BETA: opt-in feature that requires Turso configuration.
Set AGENTHUB_VECTOR_SEARCH_ENABLED=true and provide
AGENTHUB_TURSO_DATABASE_URL + AGENTHUB_TURSO_AUTH_TOKEN.
See README Vector Search (Beta) section for full setup.
```

This appears at `GET /openapi.json -> tags[]` with name `search [experimental]`. Swagger UI renders it as the description block under the experimental router group at `/docs`.

## Final CHANGELOG Entry

See `CHANGELOG.md` (newly created file). The Phase 3 section enumerates VEC-01 through VEC-06 with a one-line description each, lists the zvec removal under Removed, and documents in Notes that local SQLite returns 503 on vector endpoints and that sentence-transformers / openai are now in requirements.txt.

## README Section Location

The new `## Vector Search (Beta)` section is in `README.md` between `## Configuration` and `## Tech Stack`. This places it right after env var documentation (where users naturally look for new setting blocks) and before the implementation overview, mirroring the placement of optional features in similar OSS Python projects.

## Verification

```bash
.venv/bin/python -m pytest tests/unit/test_vector_feature_flag.py tests/integration/test_search_api.py -v --tb=short --no-cov -m "not turso"
# 48 passed (9 unit flag + 39 integration search)

.venv/bin/python -m pytest tests/ --no-cov -m "not turso"
# 135 passed, 1 skipped, 9 deselected, 133 warnings
# (Plan 05 baseline was 127 passed; +8 from Plan 06 = 135)

AGENTHUB_ADMIN_USER=x AGENTHUB_ADMIN_PASSWORD=y .venv/bin/python -c "from app.main import app; print('app boots ok')"
# app boots ok

# Acceptance grep checks (all PASS):
grep -q "vector_search_disabled" app/main.py        # OK
grep -q "openapi_tags" app/main.py                  # OK
grep -q "BETA" app/main.py                          # OK
grep -q "Vector Search (Beta)" README.md            # OK
grep -q "AGENTHUB_EMBEDDING_PROVIDER" README.md     # OK
grep -q "AGENTHUB_VECTOR_SEARCH_ENABLED" README.md  # OK
grep -q "/v1/search" README.md                      # OK
grep -q "top_k" README.md                           # OK
grep -qE "BETA|beta|experimental" CHANGELOG.md      # OK
grep -q "VEC-01" CHANGELOG.md                       # OK
grep -q "VEC-06" CHANGELOG.md                       # OK
grep -q "AGENTHUB_VECTOR_SEARCH_ENABLED" .env.example  # OK
grep -q "AGENTHUB_EMBEDDING_PROVIDER" .env.example     # OK
grep -q "AGENTHUB_OPENAI_API_KEY" .env.example         # OK

# em-dash check across all edited docs:
grep -c -- " — " README.md CHANGELOG.md .env.example
# 0 across all files (per CLAUDE.md no-em-dash rule)

# OpenAPI endpoint inspection:
.venv/bin/python -c "from fastapi.testclient import TestClient; from app.main import app; \
  c=TestClient(app); data=c.get('/openapi.json').json(); \
  tags=data.get('tags',[]); exp=[t for t in tags if 'experimental' in t.get('name','')]; \
  assert exp and 'BETA' in exp[0].get('description',''); print('ok')"
# ok
```

## Task Commits

1. **Task 1 RED**: `dc1a019` - test(03-06): add failing tests for VEC-06 beta opt-in
2. **Task 1 GREEN**: `ee4a429` - feat(03-06): VEC-06 startup warning + OpenAPI BETA tag
3. **Task 2 docs**: `021c4fb` - docs(03-06): VEC-06 README Vector Search (Beta), CHANGELOG, .env.example

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] caplog does not capture structlog PrintLoggerFactory output**
- **Found during:** Task 1 RED -> GREEN transition
- **Issue:** First cut of `test_startup_logs_warning_on_local_sqlite` and `test_startup_no_warning_when_enabled` used `caplog` to assert on structlog records. OpenHub's structlog setup uses `PrintLoggerFactory()` which writes to stdout, bypassing stdlib logging entirely. caplog stayed empty even though the warning was clearly visible in pytest's stdout capture.
- **Fix:** Switched both tests to use `capsys` and assert against `captured.out + captured.err`.
- **Files modified:** tests/integration/test_search_api.py
- **Verification:** Both tests pass after the switch; the assertion matches the JSON-rendered `vector_search_disabled` event.
- **Commit:** Folded into `dc1a019` (RED commit was iterated before commit landed).

**2. [Rule 3 - Blocking] Dead AGENTHUB_ZVEC_PATH entry in .env.example**
- **Found during:** Task 2 (.env.example edit)
- **Issue:** Plan 01 deleted `Settings.zvec_path` but left the corresponding entry in `.env.example`. Adding the new vector env vars without removing the dead entry would have left OSS users with a confusing config example pointing at a setting that no longer exists.
- **Fix:** Removed `AGENTHUB_ZVEC_PATH=./data/zvec` from the Storage section while inserting the new vector block.
- **Files modified:** .env.example
- **Verification:** `grep -q ZVEC .env.example` returns nothing.
- **Commit:** `021c4fb` (Task 2 commit).

**3. [Rule 1 - Bug] MD034 lint warning on bare Turso URL**
- **Found during:** Task 2 README edit (IDE post-Edit hook)
- **Issue:** The README's Requirements bullet had `https://turso.tech` as a bare URL, which the markdown linter flagged as MD034/no-bare-urls.
- **Fix:** Rewrote as `[turso.tech](https://turso.tech)`.
- **Files modified:** README.md
- **Verification:** No further MD034 warnings reported by the IDE hook.
- **Commit:** `021c4fb` (Task 2 commit).

---

**Total deviations:** 3 auto-fixed (1 blocking test infrastructure, 1 blocking config cleanup, 1 lint bug)
**Impact on plan:** All three were minor mechanical fixes that did not change scope. The structlog/capsys discovery is recorded as a Known Gotcha so downstream plans skip the same dead end.

## Authentication Gates

None - this plan is documentation + a couple of constructor and lifespan changes; no auth required at any step.

## Issues Encountered

None beyond the deviations listed above. The full non-turso test suite went from 127 passed in Plan 05 to 135 passed here (8 net new tests, all passing). The Turso-marked tests from Plans 02/04/05 still need to run against a real Turso DB before tagging Phase 3 complete - this was already documented in the Plan 05 SUMMARY and is unchanged by Plan 06.

## User Setup Required

None - no external service configuration is required to land this plan. The README Vector Search (Beta) section *describes* user setup for OSS users who want to enable the feature, but enabling vector search is opt-in and not required for OpenHub to run.

## Known Stubs

None.

## Phase 3 Readiness Check

VEC-01 through VEC-06 are now all marked complete in PLAN frontmatter. With Plan 06 landed:

- Vector columns + DiskANN index migration: shipped (Plan 01)
- Search service + storage tests: shipped (Plan 02)
- Embedding service (local + openai): shipped (Plan 03)
- Auto-indexing hooks + retry worker: shipped (Plan 04)
- /v1/search + reindex + delete + shortcuts: shipped (Plan 05)
- Beta opt-in flag + startup warning + OpenAPI BETA tag + README/CHANGELOG/.env.example: shipped (Plan 06)

**Outstanding for Phase 3 closeout (not blocking Plan 06):**
1. Run the 9 turso-marked tests against a real Turso DB (`export TURSO_DATABASE_URL=...; .venv/bin/python -m pytest -m turso tests/integration/`). Documented in Plan 05's SUMMARY.
2. Phase 5 OSS release should split sentence-transformers + openai into a `vector` extras_require to keep the base wheel small. Documented as a future Phase 5 action item, not in scope for Plan 06.

## Next Phase Readiness

- Phase 3 (vector-database) is functionally and contractually complete pending the Turso end-to-end smoke test
- Ready for `/gsd:verify-work 03` and then phase transition to Phase 4

## Self-Check: PASSED

- app/main.py: FOUND
- app/api/routes_search.py: FOUND
- README.md: FOUND
- CHANGELOG.md: FOUND
- .env.example: FOUND
- tests/unit/test_vector_feature_flag.py: FOUND
- tests/integration/test_search_api.py: FOUND
- .planning/phases/03-vector-database/03-06-SUMMARY.md: FOUND
- Commit dc1a019 (RED): FOUND
- Commit ee4a429 (Task 1 GREEN): FOUND
- Commit 021c4fb (Task 2 docs): FOUND

---
*Phase: 03-vector-database*
*Completed: 2026-04-13*
