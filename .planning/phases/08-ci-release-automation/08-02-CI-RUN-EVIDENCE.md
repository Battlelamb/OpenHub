# 08-02 — CI Result Follow-up

Date: 2026-05-28

## Objective

Inspect the first GitHub Actions run after 08-01 landed and fix CI-only failures without weakening CI gates.

## First run

- Commit: `be500d6` (`ci: add OpenHub GitHub Actions workflow`)
- Run: `26597548232`
- URL: `https://github.com/Battlelamb/OpenHub/actions/runs/26597548232`
- Result: failed before jobs were created (`jobs: []`)

## Root cause

Local `actionlint` found the workflow syntax/context error:

```text
.github/workflows/ci.yml:127:29: context "runner" is not allowed here.
```

The `playwright-e2e` job used `${{ runner.temp }}` in job-level `env`. GitHub does not allow the `runner` context in that location, so the workflow failed at parse/planning time and produced no job logs.

## Fix

Use a literal runner-local temp path for the E2E SQLite DB:

```yaml
AGENTHUB_DB_PATH: /tmp/openhub-e2e.db
```

This preserves the same CI behavior — isolated ephemeral SQLite state — without using a disallowed expression context.

## Verification result

Completed before pushing the fix:

- `actionlint .github/workflows/ci.yml` — passed.
- `git diff --check` — passed.
- `.planning/HANDOFF.json` parse — passed.
- GSD health — healthy.
- GSD consistency — passed with 6 known non-blocking warnings.
- Changed-file secret scan — no hits.

## GitHub Actions rerun result

- Commit: `27f1703`
- Run: `26597813831`
- URL: `https://github.com/Battlelamb/OpenHub/actions/runs/26597813831`
- Result: success

Jobs:

- Backend tests — success (`1m39s`)
- Frontend lint, tests, and build — success (`45s`)
- Compose and package smoke — success (`32s`)
- Playwright dashboard E2E — success (`2m29s`)

Advisory only: GitHub emitted Node.js 20 action deprecation notices for current `actions/*@v4/v5` actions. These did not fail CI, but Phase 08 can later add `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` or update actions when upstream support is clear.

## Final closeout run

A later documentation closeout commit also triggered CI:

- Commit: `518d2d3`
- Run: `26598053442`
- URL: `https://github.com/Battlelamb/OpenHub/actions/runs/26598053442`
- Result: success

All four jobs passed again. Node.js 20 action deprecation remained advisory-only.

## Status

08-02 is complete. Next slice: 08-03 Docker dashboard packaging.
