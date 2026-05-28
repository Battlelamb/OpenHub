---
phase: 08
slice: 08-04
name: Release/tag automation guardrail
status: complete
updated: 2026-05-28T20:56:52Z
---

# 08-04 — Release/tag Automation Guardrail

## Objective

Add a safe release verification path without creating tags, publishing packages, or requiring registry secrets.

## Implemented

- Added `.github/workflows/release.yml` as a manual-only `workflow_dispatch` workflow.
- Workflow permissions are read-only: `contents: read`.
- Required input: `version` in tag-shaped form, e.g. `v0.1.1`.
- Required input: `confirm_no_publish=true`.
- Workflow refuses to proceed when:
  - `confirm_no_publish` is not true,
  - version is not tag-shaped,
  - `pyproject.toml` version does not match the workflow input,
  - `refs/tags/<version>` already exists.
- Workflow builds/verifies artifacts only:
  - installs release tooling,
  - runs dependency drift guard,
  - runs release-focused backend/static workflow tests,
  - audits/lints/typechecks/tests/builds the dashboard,
  - builds Python distributions and runs `twine check`,
  - builds a Docker image without pushing,
  - uploads Python dist files as workflow artifacts.
- Documented the guardrail in `README.md`, `docs/OPERATIONS.md`, and `CHANGELOG.md`.

## Explicit non-actions

- No tag creation.
- No GitHub release creation.
- No PyPI publishing.
- No Docker Hub/GHCR publishing.
- No registry secrets added.

## Local verification

```text
.venv/bin/python -m pytest tests/unit/test_release_guardrail_workflow.py tests/unit/test_dependency_drift_guard.py -q --tb=short
→ 5 passed

/tmp/openhub-tools/actionlint .github/workflows/ci.yml .github/workflows/release.yml
→ passed

workflow bash -n passed for 26 run steps
```

## Remote verification

GitHub Actions run `26601647394` on commit `77f71ed` passed. The release workflow is manual-only, so normal push CI validated the static workflow guardrail tests and dependency drift guard without running release artifact builds automatically.

Run: https://github.com/Battlelamb/OpenHub/actions/runs/26601647394
