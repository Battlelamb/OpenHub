# Task 07-03 Deployment Packaging Smoke

Date: 2026-05-25T07:15:39Z
Scope: Phase 07 Task 07-03 only.

## Summary

Deployment packaging smoke found four evidence-backed documentation/configuration drifts and patched them:

- README Docker quickstart used the legacy `docker-compose` binary, but this host only has Compose v2 via `docker compose`.
- `.env.example` repeated the same legacy `docker-compose` command.
- `docker-compose.yml` set `REDIS_URL`, but OpenHub reads settings through the `AGENTHUB_` prefix, so Redis needed `AGENTHUB_REDIS_URL`.
- `docker compose config` reported the top-level `version` key as obsolete.

No changes were needed in `pyproject.toml` or `Dockerfile`.

## README and Environment Quickstart Check

Evidence:

- `command -v docker`: `/usr/bin/docker`
- `docker compose version`: `Docker Compose version v5.0.2`
- `docker-compose version`: failed with `/bin/bash: line 1: docker-compose: command not found`
- README Docker quickstart now uses `docker compose up --build`.
- `.env.example` now uses `docker compose up --build`.
- README endpoint list now states `/dashboard` is available when built web assets exist at `web/dist`.

Dashboard caveat:

- `app/main.py` mounts `/dashboard` only if `web/dist/index.html` exists.
- `Dockerfile` copies `app/`, `scripts/`, `alembic.ini`, and `alembic/`, but does not build or copy `web/dist`.
- This smoke did not add a frontend Docker build stage; Docker API health packaging and dashboard asset packaging are therefore separate concerns for the final tag decision.

## pyproject Console Command Check

Command:

```bash
python3 - <<'PY'
import ast
import tomllib
from pathlib import Path
pyproject = tomllib.loads(Path('pyproject.toml').read_text())
script = pyproject['project']['scripts'].get('openhub')
module_name, func_name = script.split(':')
module_path = Path(*module_name.split('.')).with_suffix('.py')
tree = ast.parse(module_path.read_text())
functions = {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
print(f"project.name={pyproject['project']['name']}")
print(f"openhub={script}")
print(f"target_exists={func_name in functions}")
PY
```

Result:

```text
project.name=openhub
openhub=app.main:run_server
target_exists=True
```

Conclusion: `pyproject.toml` exposes the expected `openhub` console command and its target exists.

## Dockerfile Check

Static validation:

```text
healthcheck_v1_health=True
production_cmd_no_reload=True
copies_alembic=True
non_root_user=True
```

Observed basics:

- Healthcheck calls `curl -f http://localhost:7788/v1/health`.
- Runtime command is `uvicorn app.main:app --host 0.0.0.0 --port 7788`.
- Command does not use `--reload`.
- Image creates and runs as non-root user `openhub`.
- Image includes Alembic config and migration directory.

Conclusion: no Dockerfile correction was required for the bounded API packaging smoke.

## Docker Compose Check

Secret handling:

- `.env` exists locally, but its contents were not read.
- The exact unsanitized `docker compose config` path was not used because Compose renders environment values to stdout.
- The secret-safe equivalent was run with checked-in placeholder values:

```bash
docker compose --env-file .env.example config >/tmp/openhub-compose-config.yml
```

Result: exit 0 after patches.

Rendered basics after patches:

- App service restart policy: `unless-stopped`
- Redis service restart policy: `unless-stopped`
- App healthcheck: `curl -f http://localhost:7788/v1/health`
- Redis healthcheck: `redis-cli ping`
- App volumes:
  - `./data/state:/app/data/state`
  - `./data/artifacts:/app/data/artifacts`
- Redis volume: `redis_data:/data`
- Redis URL env var: `AGENTHUB_REDIS_URL=redis://redis:6379`
- No bare `REDIS_URL` service environment remains.
- App command shape is inherited from `Dockerfile` CMD.

Initial smoke finding:

- Before patching, `docker compose --env-file .env.example config` exited 0 but warned that top-level `version` is obsolete.
- Before patching, rendered app environment used bare `REDIS_URL`, which does not match `SettingsConfigDict(env_prefix="AGENTHUB_")` in `app/config.py`.

Conclusion: Compose packaging basics validate after replacing `REDIS_URL` with `AGENTHUB_REDIS_URL` and removing the obsolete `version` key.

## Build Smoke

Requested command:

```bash
.venv/bin/python -m pip install -q build hatchling
.venv/bin/python -m build --sdist --wheel
```

Result:

```text
Successfully built openhub-0.1.0.tar.gz and openhub-0.1.0-py3-none-any.whl
```

Wheel import/entrypoint smoke:

```bash
rm -rf /tmp/openhub-wheel-smoke
.venv/bin/python -m pip install --no-deps --target /tmp/openhub-wheel-smoke dist/openhub-0.1.0-py3-none-any.whl
PYTHONPATH=/tmp/openhub-wheel-smoke .venv/bin/python - <<'PY'
from importlib.metadata import distribution
from app.main import run_server
print('wheel_install_import=ok')
dist = distribution('openhub')
eps = [ep for ep in dist.entry_points if ep.group == 'console_scripts' and ep.name == 'openhub']
print(f'console_scripts={[(ep.name, ep.value) for ep in eps]}')
print(f'run_server_callable={callable(run_server)}')
PY
```

Result:

```text
wheel_install_import=ok
console_scripts=[('openhub', 'app.main:run_server')]
run_server_callable=True
```

Initial bounded failures before installing local build tooling:

- `python -m build --sdist --wheel` failed because `python` is not on this host PATH.
- `python3 -m build --sdist --wheel` failed because the system Python does not have `build` installed.
- `.venv/bin/python -m build --sdist --wheel --no-isolation` failed before `hatchling` was installed.

Conclusion: package metadata and wheel generation are healthy when the local build frontend/backend are available.

## Live/Public Smoke

Commands:

```bash
curl -sS -m 10 https://hub.brunhilde.cloud/v1/health/simple
curl -sS -m 10 https://hub.brunhilde.cloud/v1/acn/status
```

Results:

```text
health_status=ok
acn_status_keys=agents,hub,nodes,total_agents,version
nodes=4
total_agents=4
```

This slice did not restart or redeploy production services.

The deployment packaging changes here are local repository changes only until committed, pushed, and deployed by the normal release flow.

## Files Corrected

- `README.md`
  - Replaced `docker-compose up --build` with `docker compose up --build`.
  - Clarified that `/dashboard` requires built web assets at `web/dist`.
- `.env.example`
  - Replaced the legacy `docker-compose up --build` comment with `docker compose up --build`.
- `docker-compose.yml`
  - Removed obsolete top-level `version`.
  - Replaced `REDIS_URL` with `AGENTHUB_REDIS_URL`.

## Remaining Caveats

- Docker image build was not run. This task requested Compose config smoke, not image build.
- The Dockerfile does not currently package the React dashboard assets; `/dashboard` requires `web/dist` beside the app at runtime. Keep this explicit for the final 07-06 tag/release decision.
- Build artifacts in `dist/` were generated for verification and are ignored by git.
