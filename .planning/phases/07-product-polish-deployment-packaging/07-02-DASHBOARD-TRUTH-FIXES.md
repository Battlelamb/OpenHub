# 07-02 Dashboard Truth Fixes

## Scope

Patch the misleading `/dashboard/health` surface found in 07-01. The page previously rendered raw `/v1/health` JSON, which exposed legacy counters such as `agents.connected=0` and `tasks.active=0` as if they were dashboard truth.

## Changes

- Replaced raw health JSON with three explicit truth cards:
  - **Service health** from `/v1/health`
  - **ACN registry truth** from `/v1/acn/status`
  - **Task truth** from `/v1/tasks/search?page=1&limit=100`
- Added `useAcnStatus()` and `useTaskSummary()` query hooks.
- Expanded `HealthResponse` typing so live `/v1/health` status values such as `healthy` are valid.
- Added English/Turkish health-page copy explaining why `/v1/health` is service/process health only.
- Added a Vitest regression test proving the page separates service, ACN, and task truth and does not render raw legacy counter keys as the main dashboard view.

## Verification

Commands run from `/home/brunhilde/OpenHub` unless noted:

```bash
cd web && npm run test -- --run src/routes/_authed/-health-truth.test.tsx
cd web && npm run typecheck
cd web && npm run test -- --run
cd web && npm run build
python -m pytest tests/ -x -q --tb=short
git diff --check
```

Results:

- Focused health truth test: **1 passed**
- TypeScript: **passed**
- Vitest suite: **42 passed / 16 files**
- Dashboard build: **passed**
- Backend pytest suite: **passed** (`9 skipped`, expected Turso-vector skips)
- Diff whitespace check: **passed**

## Known follow-up

- `npm run lint` currently fails because the `eslint` executable is not installed in `web/node_modules`. This is not a 07-02 code failure; it belongs to **07-04 Test/CI command alignment**.
- Live production task data still includes old E2E/demo task artifacts. The health page now labels the count truthfully; data hygiene remains a later bounded cleanup decision.
