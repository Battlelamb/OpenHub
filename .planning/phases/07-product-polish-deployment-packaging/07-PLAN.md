# Phase 07 Product Polish + Deployment Packaging Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task when code changes are needed. Keep docs-only slices direct and small.

**Goal:** Align the dashboard, docs, packaging, runtime ops notes, and release evidence with the live OpenHub system after Phase 06.

**Architecture:** Keep the existing FastAPI + React/Vite + TanStack Query + ACN architecture. Prefer fixing misleading data paths and documentation drift over adding new features. Every UI claim must be backed by backend/API behavior and verification evidence.

**Tech Stack:** Python/FastAPI, React 19, Vite, TypeScript, TanStack Query, Playwright, pytest, Vitest, systemd user services, Cloudflare Tunnel.

---

## Task 07-01: Dashboard truth audit

**Objective:** Identify any dashboard/API mismatch where the UI shows stale, legacy, or misleading state while ACN/runtime health is correct.

**Files:**
- Read: `web/src/hooks/queries/*.ts`
- Read: `web/src/routes/_authed/**/*.tsx`
- Read: `app/api/routes_acn.py`, `app/api/routes_agents.py`, `app/api/routes_tasks.py`, `app/api/routes_workflows.py`
- Create: `.planning/phases/07-product-polish-deployment-packaging/07-01-DASHBOARD-TRUTH-AUDIT.md`

**Steps:**
1. List dashboard routes and the hooks/endpoints each route calls.
2. Compare Agents route behavior against `/v1/acn/status` and `/v1/acn/health`.
3. Compare Tasks/Kanban behavior against `/v1/tasks/search`, task detail, and status PATCH.
4. Compare Workflows behavior against `/v1/workflows` and workflow detail persistence.
5. Smoke public dashboard routes and local API routes.
6. Record each finding as: route, endpoint, observed truth, misleading behavior, fix required yes/no.

**Verification:**

```bash
curl -sS https://hub.brunhilde.cloud/v1/health/simple
curl -sS https://hub.brunhilde.cloud/v1/acn/status
```

**Commit:**

```bash
git add .planning/phases/07-product-polish-deployment-packaging/07-01-DASHBOARD-TRUTH-AUDIT.md
git commit -m "docs: audit dashboard truth sources (Phase 07-01)"
```

---

## Task 07-02: Dashboard truth fixes

**Objective:** Patch any misleading dashboard/API behavior found in 07-01 and cover it with tests.

**Files:**
- Modify only files identified by `07-01-DASHBOARD-TRUTH-AUDIT.md`
- Add/modify backend tests under `tests/unit/` or `tests/integration/` if backend behavior changes
- Add/modify frontend tests under `web/src/**` if UI behavior changes
- Add/modify Playwright tests under `web/e2e/` for cross-layer behavior

**Steps:**
1. Pick one misleading behavior from the audit.
2. Write the smallest failing test that captures it.
3. Patch the backend or frontend path.
4. Run targeted tests.
5. Repeat only for findings in scope.

**Verification:**

```bash
cd /home/brunhilde/OpenHub && source .venv/bin/activate && python -m pytest tests/ -x -q --tb=short
cd /home/brunhilde/OpenHub/web && npm run test -- --run
cd /home/brunhilde/OpenHub/web && npm run build
```

**Commit:**

```bash
git add -A
git commit -m "fix: align dashboard truth sources (Phase 07-02)"
```

---

## Task 07-03: Deployment packaging smoke

**Objective:** Verify or correct the documented Docker, pip, local, and live deployment paths.

**Files:**
- Read/modify: `README.md`
- Read/modify: `Dockerfile`, `docker-compose.yml`, `pyproject.toml`
- Create: `.planning/phases/07-product-polish-deployment-packaging/07-03-DEPLOYMENT-SMOKE.md`

**Steps:**
1. Check current README quickstart against actual commands.
2. Verify `pyproject.toml` exposes the expected `openhub` console command.
3. Verify Docker Compose health/restart settings are still present.
4. Document bounded smoke results and caveats.
5. Patch docs only where evidence supports it.

**Verification:**

```bash
cd /home/brunhilde/OpenHub && python -m build --sdist --wheel
cd /home/brunhilde/OpenHub && docker compose config
```

**Commit:**

```bash
git add README.md Dockerfile docker-compose.yml pyproject.toml .planning/phases/07-product-polish-deployment-packaging/07-03-DEPLOYMENT-SMOKE.md
git commit -m "docs: verify deployment packaging paths (Phase 07-03)"
```

---

## Task 07-04: Test and CI command alignment

**Objective:** Ensure GSD and docs list commands that exist and match the current repo tooling.

**Files:**
- Modify: `.gsdrc.toml`
- Modify if needed: `README.md`
- Modify if needed: `.github/workflows/*`
- Create: `.planning/phases/07-product-polish-deployment-packaging/07-04-TEST-COMMANDS.md`

**Steps:**
1. Compare `.gsdrc.toml` verification commands to installed dependencies and package scripts.
2. Run or dry-check each command.
3. Replace stale required gates with accurate current gates.
4. Record which commands are required vs optional.

**Verification:**

```bash
cd /home/brunhilde/OpenHub && source .venv/bin/activate && python -m pytest tests/unit/test_admin_transition_status.py -q
cd /home/brunhilde/OpenHub/web && npm run typecheck
cd /home/brunhilde/OpenHub/web && npm run build
```

**Commit:**

```bash
git add .gsdrc.toml README.md .github/workflows .planning/phases/07-product-polish-deployment-packaging/07-04-TEST-COMMANDS.md
git commit -m "chore: align verification commands (Phase 07-04)"
```

---

## Task 07-05: Runtime ops cleanup docs

**Status:** ✅ Complete — see `07-05-RUNTIME-OPS.md` and `docs/OPERATIONS.md`.

**Objective:** Document the real runtime service layout and recovery checks without exposing secrets.

**Files:**
- Modify/create: `docs/operations.md` or existing operations doc
- Create: `.planning/phases/07-product-polish-deployment-packaging/07-05-RUNTIME-OPS.md`

**Steps:**
1. Record active service names: `openhub-api.service`, `openhub-bridge-brunhilde.service`.
2. Record disabled legacy service: `openhub-bridge.service`.
3. Add secret-safe diagnostics for API, bridge, ACN, and public health.
4. Add recovery notes for stale bridge/API states.
5. Verify all commands redact keys.

**Verification:**

```bash
systemctl --user status openhub-api.service --no-pager
systemctl --user status openhub-bridge-brunhilde.service --no-pager
curl -sS http://127.0.0.1:7788/v1/acn/status
```

**Commit:**

```bash
git add docs .planning/phases/07-product-polish-deployment-packaging/07-05-RUNTIME-OPS.md
git commit -m "docs: document runtime operations cleanup (Phase 07-05)"
```

---

## Task 07-06: Full verification and tag decision

**Status:** ✅ Complete — see `07-06-VERIFICATION.md`; release tag deferred pending explicit version choice.

**Objective:** Produce final evidence for whether to tag the next release.

**Files:**
- Modify: `.planning/STATE.md`
- Modify: `CHANGELOG.md` if tagging
- Create: `.planning/phases/07-product-polish-deployment-packaging/07-06-VERIFICATION.md`

**Steps:**
1. Run backend tests.
2. Run frontend tests.
3. Run frontend build.
4. Run Playwright E2E.
5. Smoke live health, ACN, and dashboard routes.
6. Record evidence and decide whether to tag.

**Verification:**

```bash
cd /home/brunhilde/OpenHub && source .venv/bin/activate && python -m pytest tests/ -x -q --tb=short
cd /home/brunhilde/OpenHub/web && npm run test -- --run
cd /home/brunhilde/OpenHub/web && npm run build
cd /home/brunhilde/OpenHub/web && npx playwright test --reporter=list
curl -sS https://hub.brunhilde.cloud/v1/health/simple
curl -sS https://hub.brunhilde.cloud/v1/acn/status
```

**Commit:**

```bash
git add CHANGELOG.md .planning/STATE.md .planning/phases/07-product-polish-deployment-packaging/07-06-VERIFICATION.md
git commit -m "docs: record Phase 07 verification evidence"
```
