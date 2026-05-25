# 07-04 Test/CI Command Alignment

**Status:** Complete  
**Completed:** 2026-05-25T04:07:56Z  
**Slice type:** GSD tooling + verification alignment

## Objective

Resolve the missing frontend lint executable and align GSD verification commands with the checks that are currently installed, reproducible, and meaningful for OpenHub.

## Changes

- Refreshed local GSD surfaces with:
  - `npx -y get-shit-done-cc@latest --claude --hermes --local --profile=core --portable-hooks`
- Installed frontend lint tooling in `web/package.json` / `web/package-lock.json`:
  - `eslint`
  - `@eslint/js`
  - `typescript-eslint`
  - `eslint-plugin-react-hooks`
  - `eslint-plugin-react-refresh`
  - `globals`
- Added `web/eslint.config.js` flat config for the Vite/React/TypeScript dashboard.
- Upgraded `vitest` to `^4.1.7` after `npm audit fix` left a vulnerable nested Vite/esbuild path.
- Updated `.gsdrc.toml` verification commands so the GSD loop now runs current passing gates:
  - backend pytest through `.venv`
  - frontend npm audit
  - frontend lint
  - frontend typecheck
  - frontend Vitest
  - frontend build
- Kept the backend strict lint command as `backend_lint_baseline` for the future backend-format/type cleanup slice instead of making it a required gate while the current app tree has pre-existing formatting drift.

## Evidence

```bash
gsd-sdk --version
# gsd-sdk v1.42.3

python3 - <<'PY'
# JSON/TOML validation for .gsd/provider-config.json, .claude/settings.json,
# .hermes/settings.json, web/package.json, and .gsdrc.toml
PY
# all parsed successfully

# secret scan across .claude, .hermes, .gsd, and web config/package files
# secret_scan_hits=none

cd web && npm audit --audit-level=moderate
# found 0 vulnerabilities

cd web && npm run lint -- --max-warnings=0
# passed

cd web && npm run typecheck
# passed

cd web && npm run test -- --run
# 16 files / 42 tests passed

cd web && npm run build
# passed

source .venv/bin/activate && pytest -q --tb=short --disable-warnings
# passed with expected Turso-vector skips
```

## Noted baseline drift

The Python strict lint/format baseline is installed and callable (`black`, `isort`, `flake8`, `mypy` all exist in `.venv`), but `black --check app/` currently reports broad pre-existing formatting drift across the backend. This slice did **not** mass-format backend files, because that would be a high-churn follow-up unrelated to restoring the missing dashboard lint gate.

## Result

`npm run lint` is no longer blocked. GSD verification now has a passing current command set, while the backend strict lint baseline remains explicit for a focused future cleanup.
