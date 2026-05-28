# 08-01 — GitHub Actions CI Workflow

Date: 2026-05-28

## Objective

Add the first committed GitHub Actions CI workflow for OpenHub so backend, frontend, package/Compose, and dashboard E2E checks run automatically on push, pull request, and manual dispatch.

## Files

- `.github/workflows/ci.yml`
- `.planning/phases/08-ci-release-automation/08-PLAN.md`
- `.planning/phases/08-ci-release-automation/08-01-CI-WORKFLOW.md`
- `.planning/phases/08-ci-release-automation/.continue-here.md`
- `.planning/STATE.md`
- `.planning/ROADMAP.md`
- `.planning/HANDOFF.json`

## CI workflow shape

- `backend-tests`
  - Python 3.11
  - `pip install -r requirements.txt`
  - `pip install -e .`
  - `python -m pytest tests/ -q --tb=short --disable-warnings`

- `frontend-tests`
  - Node 22
  - `npm ci`
  - `npm audit --audit-level=moderate`
  - `npm run lint -- --max-warnings=0`
  - `npm run typecheck`
  - `npm run test -- --run`
  - `npm run build`

- `compose-and-package-smoke`
  - `docker compose --env-file .env.example config`
  - `python -m build`
  - `twine check dist/*`
  - wheel metadata check for `openhub = app.main:run_server`

- `playwright-e2e`
  - Python + Node install
  - build dashboard assets
  - install Chromium
  - start ephemeral local OpenHub on port `7788`
  - wait for `/v1/health/simple`
  - run `npx playwright test --reporter=list`

## Secret posture

- No real `ak_...`, `oh_...`, provider, GitHub, Docker, or PyPI tokens are stored.
- CI uses dummy deterministic admin/JWT values and a runner temp SQLite DB.
- Release/publish jobs are intentionally out of scope for 08-01.

## Local verification plan

Before commit/push:

1. Validate YAML parseability when PyYAML is available.
2. Run repo-local GSD health and consistency.
3. Run changed-file secret scan.
4. Run focused local smoke commands:
   - `python -m pytest tests/unit/test_static_mount.py tests/unit/test_admin_dashboard_auth.py -q --tb=short`
   - `cd web && npm run typecheck`
5. Confirm intended diff only.
6. Commit and push.
7. Verify local/origin/remote equality.

## Local verification result

Completed before commit/push:

- `git diff --check` — passed.
- Workflow shape parse — passed; PyYAML loaded 4 jobs: `backend-tests`, `frontend-tests`, `compose-and-package-smoke`, `playwright-e2e`.
- `.planning/HANDOFF.json` parse — passed.
- GSD health — healthy.
- GSD consistency — passed with 6 known non-blocking warnings after adding the Phase 08 super-plan warning.
- Changed-file secret scan — no hits.
- Focused backend smoke — 8 passed (`test_static_mount.py`, `test_admin_dashboard_auth.py`).
- Frontend typecheck — passed.

## Follow-up

08-02 should inspect the first GitHub Actions run and patch any CI-only failures with focused evidence.
