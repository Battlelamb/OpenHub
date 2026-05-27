# 07-06 Verification + Tag Decision

Date: 2026-05-27
Evidence directory: `/tmp/openhub-07-06-20260527T170331Z-gsd-fixes`
Summary file: `/tmp/openhub-07-06-20260527T170331Z-gsd-fixes/summary.tsv`

## Result

✅ Full 07-06 gate passed.

All verification steps exited `0`:

| Gate | Result | Evidence |
|---|---:|---|
| Backend tests | ✅ 249 passed / 9 skipped | `backend_pytest.log` |
| Frontend audit | ✅ 0 vulnerabilities | `frontend_audit.log` |
| Frontend lint | ✅ passed | `frontend_lint.log` |
| Frontend typecheck | ✅ passed | `frontend_typecheck.log` |
| Frontend tests | ✅ 42 passed / 16 files | `frontend_vitest.log` |
| Frontend build | ✅ built | `frontend_build.log` |
| Playwright E2E | ✅ 10 passed | `playwright.log` |
| Docker Compose config render | ✅ passed | `compose_config.log` |
| GSD health | ✅ healthy | `gsd_health.log` |
| GSD consistency | ✅ passed | `gsd_consistency.log` |
| Local services | ✅ API + bridge active/enabled | `local_services.log` |
| Public health | ✅ `/v1/health/simple` OK | `live_health.log` |
| Public ACN status | ✅ `/v1/acn/status` OK | `live_acn_status.log` |
| Dashboard route smoke | ✅ `/dashboard*` routes 200 | `dashboard_routes.log` |
| Post-deploy restart verification | ✅ local/public health, ACN, dashboard, heartbeat scan | `post_deploy_restart_verify.log` |

## Changes made during this gate

The gate found two actionable issues, both fixed with targeted coverage:

1. Heartbeat timestamp advisory became reproducible.
   - Pre-fix live logs repeatedly showed `heartbeat_check_failed` with `can't compare offset-naive and offset-aware datetimes`.
   - Added regression coverage in `tests/unit/test_heartbeat_service_timezone.py`.
   - Fixed `app/services/heartbeat_service.py` by normalizing legacy naive timestamps to UTC-aware datetimes before threshold comparison.
   - Restarted `openhub-api.service` and rechecked logs since restart; no `heartbeat_check_failed`, `offset-naive`, or `offset-aware` matches remained.

2. Kanban Playwright drag/drop was flaky under keyboard DnD in this grid layout.
   - `web/e2e/dashboard.spec.ts` now uses explicit mouse drag from the real drag handle to the claimed-column dropzone.
   - Full Playwright suite passed after the update.

## Live smoke after API restart

`post_deploy_restart_verify.log` records the post-fix runtime verification:

- Local `/v1/health/simple` → OK
- Public `/v1/health/simple` → OK
- Public `/v1/acn/status` → `version=0.1.0`, `nodes=8`, `total_agents=8`, `online_agents=1`
- `/dashboard`, `/dashboard/tasks`, `/dashboard/agents`, `/dashboard/health` → 200
- `openhub-api.service`, `openhub-bridge-brunhilde.service` → active
- Heartbeat error scan since restart → no matches

## Non-blocking notes

- Closeout rechecks after documentation updates: targeted heartbeat regression passed; `.planning/HANDOFF.json` parsed; GSD health returned healthy; GSD consistency passed with the same 5 known warnings; changed-file secret scan found no hits.
- Backend vector integration tests skipped where Turso credentials are intentionally absent in local test mode.
- Backend run still emits existing dependency/runtime warnings; none failed the gate.
- Vite still warns that the main dashboard chunk is larger than 500 kB; this remains a future bundle-splitting polish item, not a release blocker.
- GSD consistency passes with 5 known non-blocking warnings about legacy/super-plan frontmatter and missing `SUMMARY.md` files.

## Tag decision

No release tag was created in this slice.

Reason: 07-06 discovered and fixed a real runtime heartbeat advisory and an E2E reliability issue. The correct closeout is to commit, push, deploy/restart, and verify equality first. The repository remains package version `0.1.0`, and the live `/v1/acn/status` payload also reports `0.1.0`.

Recommended next release action after this commit is clean on origin:

- Use `v0.1.1` if tagging only the heartbeat/log-noise fix plus verification polish.
- Use `v0.2.0` if tagging the broader Phase 06/07 product additions: Kanban, Workflow Canvas, dashboard truth fixes, runtime ops docs, and verification evidence.

## Verdict

Phase 07 verification is complete and release-ready after the closeout commit/push/deploy verification. Tagging is intentionally deferred to an explicit version/tag command.
