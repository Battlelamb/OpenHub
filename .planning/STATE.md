---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: OpenHub v1.0
status: Phase 08 CI + Release Automation complete — release tag deferred pending explicit version decision
stopped_at: "PHASE-08-COMPLETE"
last_updated: "2026-05-31T07:49:37Z"
progress:
  total_phases: 8
  completed_phases: 8
  total_plans: 56
  completed_plans: 56
---

# Project State

## Project Reference

See: `.planning/PROJECT.md` and `.planning/ROADMAP.md`.

**Core value:** Any developer can self-host OpenHub, connect AI agents, and coordinate multi-agent workflows from a single command center — reliably and without conflicts.

**Current focus:** Phase 08 CI + release automation is complete. Release/tag creation remains deferred until the operator explicitly chooses a version and target.

## Current Position

- **Status:** complete
- **Current phase:** 08 — CI + Release Automation
- **Current plan:** `.planning/phases/08-ci-release-automation/08-PLAN.md`
- **Current slice:** `Phase 08 complete`
- **Next slice:** explicit release version/tag decision or future roadmap planning
- **Previous phase:** 07 — Product Polish + Deployment Packaging complete
- **Live status:** `https://hub.brunhilde.cloud` healthy; ACN status endpoint reports 10 agents / 1 online from latest smoke

## Phase 05 Progress (COMPLETE)

| Slice | Description | Status | Commit |
|-------|-------------|--------|--------|
| 05-01 | GSD loop initialization | ✅ | 85b9a15 |
| 05-02 | Release-readiness snapshot | ✅ | 3526240 |
| 05-03 | Stuck work recovery UX | ✅ | 263cfe4 |
| 05-04 | Graceful shutdown | ✅ | 809f4dc |
| 05-05 | Docker Compose hardening | ✅ | ce6b75e |
| 05-06 | pip install path | ✅ | 491f3b1 |
| 05-07 | README quickstart polish | ✅ | 6747d11 |
| 05-08 | Playwright E2E tests | ✅ | 4cab1db |

## Phase 06 Progress (COMPLETE)

| Slice | Description | Status | Commit |
|-------|-------------|--------|--------|
| 06-01 | Backend unit tests: admin_transition_status | ✅ | 44bc53a |
| 06-02 | Backend integration tests: PATCH endpoint | ✅ | f74bb94 |
| 06-03 | Kanban + Workflow Canvas scaffold with backend transition hook | ✅ | 518cc66 |
| 06-04 | Frontend component tests: KanbanBoard | ✅ | ed90ce1 |
| 06-05 | E2E verification: drag-drop → API → DB/refetch | ✅ | ec58e47 |
| 06-06 | Full verification + STATE.md update | ✅ | 0b0895d |

### Post-Phase 06 hardening

- `9ee4c64` — Kanban cards navigate to task details
- `8bc9ad4` — Workflow canvas shown on task details
- `299de29` — Workflow runtime persists across requests
- `8801fc1` — Task workflow detail context panel
- `993622b` — Legacy dashboard seed rows tolerated

## Phase 07 Progress (COMPLETE)

| Slice | Description | Status |
|-------|-------------|--------|
| 07-01 | Dashboard truth audit | ✅ |
| 07-02 | Dashboard truth fixes | ✅ |
| 07-03 | Deployment packaging smoke | ✅ |
| 07-04 | Test/CI command alignment | ✅ Done early |
| 07-05 | Runtime ops cleanup docs | ✅ |
| 07-06 | Full verification + tag decision | ✅ |

## Phase 08 Progress (COMPLETE)

| Slice | Description | Status |
|-------|-------------|--------|
| 08-01 | GitHub Actions CI workflow | ✅ |
| 08-02 | CI result follow-up | ✅ |
| 08-03 | Docker dashboard packaging | ✅ |
| 08-04 | Release/tag automation guardrail | ✅ |
| 08-05 | Dependency drift guard | ✅ |

## Verification Status

- **Backend:** 07-06 full suite passed (`python -m pytest tests/ -x -q --tb=short`) with 249 passed / 9 skipped; added naive/aware heartbeat regression coverage.
- **Backend focused Phase 06:** 35 passed (`test_admin_transition_status.py`, `test_patch_task_status_endpoint.py`)
- **Frontend:** 42 passed / 16 files on Vitest `v4.1.7`; 07-02 health truth regression included
- **Build:** `npm run build` passed for 07-06 dashboard bundle
- **Lint:** `npm run lint -- --max-warnings=0` passes with local ESLint flat config
- **Audit:** `npm audit --audit-level=moderate` reports 0 vulnerabilities
- **Backend strict lint baseline:** tools are installed, but `black --check app/` has broad pre-existing formatting drift; kept as `backend_lint_baseline` rather than a required GSD gate
- **E2E:** 10 passed (Playwright), including Kanban drag-drop API persistence via real drag handle/dropzone
- **Planning/GSD validation:** repo-local `gsd-tools.cjs validate health` healthy; `validate consistency` passed. `/gsd-progress` artifact analyzer reconciled to 38/38 after adding umbrella summaries
- **GSD Redux next integration (2026-05-25):** local Claude Code + Hermes Agent surfaces refreshed from `open-gsd/get-shit-done-redux` `next` commit `dc4b90a`; full profile installed with 67 commands/skills and 33 agents per runtime; `validate health` healthy; `validate consistency` passed; changed-file secret scan clean
- **Codex GSD runtime integration (2026-05-25):** local Codex surface added from the same `next` commit; full profile installed with 67 skills, 33 agent markdown files, and 33 agent TOML configs; Codex CLI `0.132.0`; Codex-surface `validate health` healthy; `validate consistency` passed
- **GSD model default alignment (2026-05-25):** `.planning/config.json`, `.gsd/provider-config.json`, and `.gsdrc.toml` now default to OpenAI Codex / GPT 5.5 with max effort / xhigh reasoning; Codex + Hermes GSD health/consistency passed; focused backend tests passed; changed-file secret scan clean
- **Deployment packaging smoke (2026-05-25):** `python -m build` succeeded via `.venv` after installing local build frontend/backend; wheel import and `openhub=app.main:run_server` console script verified; `docker compose --env-file .env.example config` rendered successfully with healthchecks, restart policies, volumes, and `AGENTHUB_REDIS_URL`; README, `.env.example`, and Compose drift patched
- **Live smoke (2026-05-27 after API restart):**
  - `https://hub.brunhilde.cloud/v1/health/simple` → 200 OK
  - `https://hub.brunhilde.cloud/v1/acn/status` → 200 OK; status payload reports 8 agents / 1 online
  - `/dashboard`, `/dashboard/tasks`, `/dashboard/agents`, `/dashboard/health` → 200 OK
  - API and Brunhilde bridge user services → active; heartbeat log scan since restart found no naive/aware comparison errors
- **Runtime ops cleanup docs (2026-05-26):** `docs/OPERATIONS.md` now records active user services, disabled legacy bridge, Cloudflare Tunnel route, secret-safe diagnostics, env permissions, recovery checks, and release-verification follow-up for heartbeat timestamp log noise.
- **07-06 release gate (2026-05-27):** full backend/frontend/E2E/GSD/live verification passed; heartbeat timestamp advisory fixed and deployed via `openhub-api.service` restart; tag creation deferred pending explicit version decision.

- **Docker dashboard packaging (2026-05-28):** CI run `26600306093` passed on `2ca0fb0`; Compose/package smoke built the Docker image, ran the container, verified `/v1/health/simple`, served `/dashboard`, fetched a bundled `/dashboard/assets/<hash>.js|css` asset, then verified package metadata.
- **Release guardrail + dependency drift guard (2026-05-28):** manual read-only release verification workflow added; no tag/publish path; dependency drift guard added to CI and GSD; local full backend, frontend, actionlint, workflow bash, package build/twine, GSD health/consistency, Compose config all passed. GitHub Actions run `26601647394` passed all five jobs on commit `77f71ed`.

## Session Continuity

- **Last state update:** 2026-05-31T07:49:37Z
- **Stopped at:** Phase 08 complete; release tag/version still requires explicit operator decision.
- **Resume file:** `.planning/phases/08-ci-release-automation/.continue-here.md`
- **Continue file:** `.planning/phases/08-ci-release-automation/.continue-here.md`
- **Phase 08 plan:** `.planning/phases/08-ci-release-automation/08-PLAN.md`
- **Previous verification evidence:** `.planning/phases/07-product-polish-deployment-packaging/07-06-VERIFICATION.md`
