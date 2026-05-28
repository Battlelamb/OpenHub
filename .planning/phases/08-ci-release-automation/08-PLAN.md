---
phase: 08
name: CI + Release Automation
status: in_progress
created: 2026-05-28
owner: OpenHub GSD
---

# Phase 08 — CI + Release Automation

> **For Hermes:** Use `openhub-operations`, `writing-plans`, and `test-driven-development` for implementation slices. Use repo-local GSD validation before every commit.

## Goal

Make OpenHub continuously verifiable from GitHub: backend, frontend, packaging, Docker Compose rendering, and browser E2E gates should run automatically without leaking local credentials.

## Why this phase now

Phase 07 made the local/live system clean and release-ready, but `.planning/codebase/CONCERNS.md` still lists **CI workflow absence** and **dashboard packaging verification** as critical release gaps. A public/self-hostable OpenHub needs repeatable checks on every push and pull request before additional product growth.

## Architecture

- GitHub Actions is the first CI surface.
- Keep permanent secrets out of CI: use deterministic dummy `AGENTHUB_*` credentials for tests and local SQLite temp state.
- Split CI into bounded jobs so failures point to the correct layer:
  - backend tests
  - frontend audit/lint/typecheck/tests/build
  - Compose + Python package smoke
  - Playwright dashboard E2E against an ephemeral local OpenHub process
- Keep release/tag automation as an explicit later slice; do not publish packages or create tags without operator instruction.

## Success criteria

1. `.github/workflows/ci.yml` exists and mirrors the verified GSD gates where practical.
2. CI can run on `push`, `pull_request`, and `workflow_dispatch`.
3. CI uses only dummy test credentials and local temp DB state.
4. Package smoke checks `python -m build`, `twine check`, and `openhub = app.main:run_server` console script metadata.
5. Playwright E2E builds the dashboard, starts the API, waits for health, and runs the existing dashboard suite.
6. Planning state, roadmap, handoff, and evidence all name Phase 08 as active.
7. Local validation and changed-file secret scan pass before commit/push.

## Slices

### 08-01 — GitHub Actions CI workflow

**Objective:** Add the initial GitHub Actions workflow for backend, frontend, package/Compose smoke, and Playwright E2E.

**Files:**

- Create: `.github/workflows/ci.yml`
- Create/update evidence: `.planning/phases/08-ci-release-automation/08-01-CI-WORKFLOW.md`
- Update: `.planning/STATE.md`, `.planning/ROADMAP.md`, `.planning/HANDOFF.json`

**Verification:**

- Parse/read workflow shape locally.
- Run repo-local GSD health/consistency.
- Run changed-file secret scan.
- Run a focused local subset when practical:
  - backend focused smoke: `python -m pytest tests/unit/test_static_mount.py tests/unit/test_admin_dashboard_auth.py -q --tb=short`
  - frontend command availability: `cd web && npm run typecheck`
- Commit and push.
- Verify `HEAD = origin/master = remote/master`.

### 08-02 — CI result follow-up

**Objective:** Inspect GitHub Actions run results after the workflow lands and fix CI-only failures.

**Files:**

- Modify CI workflow or code/tests only if a real CI gap appears.
- Evidence: `.planning/phases/08-ci-release-automation/08-02-CI-RUN-EVIDENCE.md`

**Verification:**

- Use `gh run list` / GitHub API to read the workflow run.
- Fix failures with focused tests first.
- Push follow-up commit only if needed.

### 08-03 — Docker dashboard packaging

**Objective:** Build the React dashboard into the Docker image and prove `/dashboard` plus hashed assets are served by the running container.

**Files:**

- `Dockerfile`
- `.dockerignore`
- `.github/workflows/ci.yml`
- `README.md`
- `docs/OPERATIONS.md`
- packaging smoke docs/evidence

**Verification:**

- Build dashboard assets locally.
- Add static tests that guard Dockerfile/.dockerignore packaging intent.
- Build Docker image locally if Docker socket is available.
- Prove `/dashboard` is served from the image through CI container smoke when local Docker is unavailable.

### 08-04 — Release/tag automation guardrail

**Objective:** Add a safe, manual release workflow or documented command path that prepares artifacts without auto-publishing secrets.

**Files:**

- Optional: `.github/workflows/release.yml`
- `CHANGELOG.md`
- docs release section

**Verification:**

- Manual trigger only.
- No PyPI/Docker publishing unless the required secrets are intentionally configured.
- Tag/version bump remains explicit.

### 08-05 — Dependency drift guard

**Objective:** Catch drift between `requirements.txt`, `pyproject.toml`, and `web/package-lock.json` earlier.

**Files:**

- Optional script under `scripts/`
- Tests or CI step
- Docs/evidence

**Verification:**

- Script exits non-zero on intentionally simulated drift.
- CI includes the guard after it is stable.

## Non-goals

- No automatic tag creation in 08-01.
- No PyPI or Docker Hub upload in 08-01.
- No broad refactor of route modules in this phase.
- No local secret/env file reads beyond safe env var names.

## Current next task

Continue with **08-04 — Release/tag automation guardrail**.
