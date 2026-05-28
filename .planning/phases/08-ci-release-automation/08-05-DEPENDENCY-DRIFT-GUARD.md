---
phase: 08
slice: 08-05
name: Dependency drift guard
status: implemented_local_ci_pending
updated: 2026-05-28T20:47:30Z
---

# 08-05 — Dependency Drift Guard

## Objective

Detect dependency drift before release work by comparing backend Python manifests and frontend package manifests in CI.

## Implemented

- Added `scripts/check_dependency_drift.py`.
- Added regression tests in `tests/unit/test_dependency_drift_guard.py`.
- Added static release workflow safety tests in `tests/unit/test_release_guardrail_workflow.py`.
- Added **Dependency drift guard** job to `.github/workflows/ci.yml`.
- Added the drift guard to `.gsdrc.toml` verify commands and command aliases.
- Documented the command in `README.md`, `docs/OPERATIONS.md`, and `CHANGELOG.md`.

## Guard behavior

Backend checks:

- Every runtime dependency in `pyproject.toml` must be pinned in `requirements.txt`.
- Every pinned dependency in `requirements.txt` must be declared in `pyproject.toml` runtime or optional dependency groups.
- Requirement pins (`==`) must match pyproject lower bounds (`>=`).
- Extras must match for packages like `uvicorn[standard]` and `pyjwt[crypto]`.

Frontend checks:

- `web/package-lock.json` lockfile root `dependencies` must match `web/package.json` exactly.
- `web/package-lock.json` lockfile root `devDependencies` must match `web/package.json` exactly.

## Local verification

```text
python scripts/check_dependency_drift.py
→ Dependency drift guard passed:
  - backend pins checked: 25
  - pyproject dependencies known: 29 (20 runtime)
  - frontend specs checked: 28 dependencies, 24 devDependencies

.venv/bin/python -m pytest tests/unit/test_release_guardrail_workflow.py tests/unit/test_dependency_drift_guard.py -q --tb=short
→ 5 passed

/tmp/openhub-tools/actionlint .github/workflows/ci.yml .github/workflows/release.yml
→ passed

workflow bash -n passed for 26 run steps
```

## Remote verification

Pending first push. Expected CI addition: a fast `dependency-drift` job on push/pull_request/workflow_dispatch.
