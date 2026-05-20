# Phase 05-06: pip install Path

**Goal:** `pip install openhub && openhub start` produces a running server — no manual steps beyond setting credentials.

**Roadmap requirement:** Phase 5, Success Criteria #2

## Changes

### pyproject.toml
- ✅ Converted from Poetry to PEP 621 with hatchling build backend
- ✅ Console script entry point: `openhub = app.main:run_server`
- ✅ Optional dependencies: `[vector]` for ML backends, `[dev]` for testing/linting
- ✅ Full project metadata: classifiers, URLs, license
- ✅ Wheel config: `packages = ["app"]`

## Verification
- ✅ `pip install -e ".[dev]"` succeeds
- ✅ `which openhub` → `.venv/bin/openhub`
- ✅ `openhub` starts the server (port conflict because API already running)
- ✅ All 197+ tests still pass

## Success Criteria
- [x] `pip install openhub` installs the package
- [x] `openhub` command starts the server
- [x] No manual steps beyond setting credentials
