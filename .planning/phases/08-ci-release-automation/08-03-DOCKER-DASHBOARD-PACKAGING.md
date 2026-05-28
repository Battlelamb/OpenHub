# 08-03 — Docker Dashboard Packaging

Date: 2026-05-28

## Objective

Make Docker dashboard packaging explicit and release-gated: the runtime image must contain the compiled React dashboard and prove `/dashboard` plus hashed assets are served from the container, not from a developer checkout.

## Changes

- `Dockerfile`
  - Added `node:22-slim AS dashboard-build` stage.
  - Runs `npm ci` and `npm run build` inside `web/` inputs.
  - Copies `/dashboard/dist` into final Python image at `./web/dist`, matching `app.main`'s static mount path.
- `.dockerignore`
  - Added as a tracked file.
  - Keeps `web/node_modules` and generated dashboard artifacts out of build context while allowing source/config/package inputs needed by the Node build stage.
- `.gitignore`
  - Stops ignoring `.dockerignore` so packaging context is reviewed and versioned.
- `.github/workflows/ci.yml`
  - Adds Docker image build to the Compose/package smoke job.
  - Starts the image on `127.0.0.1:7789`, checks `/v1/health/simple`, fetches `/dashboard`, extracts one `/dashboard/assets/<hash>.js|css` URL from HTML, and verifies the asset response headers.
- `tests/unit/test_docker_dashboard_packaging.py`
  - Guards Dockerfile multi-stage dashboard build/copy contract.
  - Guards `.dockerignore` from excluding required dashboard build inputs.
- `README.md` and `docs/OPERATIONS.md`
  - Document Docker dashboard verification and distinguish Docker-bundled assets from pip/development runs.

## Local verification

Passed:

- `npm run build` in `web/`
- `.venv/bin/python -m pytest tests/unit/test_docker_dashboard_packaging.py -q --tb=short` — 2 passed
- `.venv/bin/python -m pytest tests/unit/test_static_mount.py tests/unit/test_docker_dashboard_packaging.py -q --tb=short` — 8 passed
- `/tmp/openhub-tools/actionlint .github/workflows/ci.yml` — passed
- workflow YAML parse: 4 jobs; Compose/package smoke now has 7 steps
- `git diff --check` — passed

Local Docker limitation:

- `docker info` failed with Docker socket permission denied.
- `sudo -n docker info` failed because sudo requires a password.

Therefore the container runtime proof is delegated to GitHub Actions, where Docker is available. The CI smoke step is intentionally strict and must prove API health, dashboard HTML, and at least one bundled dashboard asset from the running image.

## CI verification

Run `26600306093` on commit `2ca0fb0` passed: https://github.com/Battlelamb/OpenHub/actions/runs/26600306093

- Backend tests — success (`1m35s`)
- Frontend lint, tests, and build — success (`41s`)
- Compose and package smoke — success (`2m25s`)
  - `Render Docker Compose config` — success
  - `Build Docker image with bundled dashboard` — success
  - `Smoke Docker dashboard packaging` — success
  - `Build Python package and validate metadata` — success
  - `Verify openhub console script from wheel` — success
- Playwright dashboard E2E — success (`2m36s`)

The Docker dashboard packaging proof is complete: CI built the image, ran the container, verified `/v1/health/simple`, verified `/dashboard`, extracted a bundled `/dashboard/assets/<hash>.js|css` asset from the served HTML, and verified the asset response headers.

Advisory: GitHub Actions still emits non-blocking Node.js 20 action deprecation notices for current `actions/*` versions.
