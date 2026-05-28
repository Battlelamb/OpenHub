# OpenHub Operations Runbook

This runbook records the verified runtime layout for the live OpenHub instance and gives secret-safe recovery checks for operators.

Last verified: 2026-05-26T06:46:33Z
Live URL: https://hub.brunhilde.cloud
Local origin: http://127.0.0.1:7788

## Runtime topology

| Component | Verified value |
|---|---|
| API service | `openhub-api.service` (`systemd --user`) |
| API command | `/home/brunhilde/OpenHub/.venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 7788` |
| API working directory | `/home/brunhilde/OpenHub` |
| API environment file | `/home/brunhilde/OpenHub/.env` (`0600`) |
| Bridge service | `openhub-bridge-brunhilde.service` (`systemd --user`) |
| Bridge command | `/home/brunhilde/OpenHub/.venv/bin/python3 scripts/run_bridge.py --agent brunhilde --hub http://localhost:7788 --heartbeat 60` |
| Bridge environment file | `/home/brunhilde/.config/openhub/bridge.env` (`0600`) |
| Legacy bridge service | `openhub-bridge.service` is disabled and inactive |
| Public edge | `cloudflared.service` system service |
| Public route | `hub.brunhilde.cloud -> http://127.0.0.1:7788` |

Do not put `ak_...`, `oh_...`, provider API keys, or Cloudflare tunnel tokens into docs, chat, git commits, or process command lines. Prefer protected environment files with mode `0600`.

## Normal health checks

Use these checks first. They do not print secrets.

```bash
# Service state
systemctl --user --no-pager status openhub-api.service openhub-bridge-brunhilde.service
systemctl --user is-enabled openhub-api.service openhub-bridge-brunhilde.service
systemctl --user is-active openhub-api.service openhub-bridge-brunhilde.service

# Confirm the old bridge stays disabled
systemctl --user is-enabled openhub-bridge.service || true
systemctl --user is-active openhub-bridge.service || true

# Local API health
curl -sS -m 5 http://127.0.0.1:7788/v1/health/simple
curl -sS -m 8 http://127.0.0.1:7788/v1/acn/status

# Public API health
curl -sS -m 8 https://hub.brunhilde.cloud/v1/health/simple
curl -sS -m 12 https://hub.brunhilde.cloud/v1/acn/status

# Public dashboard route smoke
for path in /dashboard /dashboard/tasks /dashboard/agents /dashboard/health; do
  printf '%s ' "$path"
  curl -sS -o /dev/null -m 8 -w '%{http_code}\n' "https://hub.brunhilde.cloud$path"
done
```

Expected healthy result:

- API service: `enabled`, `active`.
- Bridge service: `enabled`, `active`.
- Legacy bridge: `disabled`, `inactive`.
- Local and public `/v1/health/simple`: HTTP 200.
- Local and public `/v1/acn/status`: HTTP 200 and non-zero agents/nodes when bridges are connected.
- Dashboard routes: HTTP 200.

## Docker image dashboard smoke

The Docker image is expected to build the React dashboard in a Node stage and copy the resulting `web/dist` bundle into the Python runtime image. A Docker smoke should prove both API health and dashboard asset serving from the container, not from the checkout.

```bash
docker build -t openhub:local-smoke .
docker run --rm -d --name openhub-local-smoke \
  -p 127.0.0.1:7789:7788 \
  --env-file .env.example \
  -e AGENTHUB_DB_PATH=/tmp/openhub-smoke.db \
  -e AGENTHUB_ARTIFACT_DIR=/tmp/openhub-artifacts \
  openhub:local-smoke

curl -sS -m 8 http://127.0.0.1:7789/v1/health/simple
curl -sS -m 8 http://127.0.0.1:7789/dashboard | grep 'id="root"'
# Then fetch one /dashboard/assets/<hash>.js or .css URL from the HTML and verify HTTP 200.

docker stop openhub-local-smoke
```

CI runs the same class of proof in `.github/workflows/ci.yml` under **Compose and package smoke**.

## Secret-safe process and port inspection

```bash
ps -eo pid,ppid,lstart,etime,cmd \
  | grep -Ei '[o]penhub|[r]un_bridge|uvicorn app\.main' \
  | sed -E 's/(--api-key )[A-Za-z0-9_\-]+/\1[redacted]/g; s/(oh_)[A-Za-z0-9]+/\1[redacted]/g; s/(ak_)[A-Za-z0-9]+/\1[redacted]/g'

ss -ltnp | grep -E ':7788|uvicorn|python' || true

stat -c '%a %U:%G %n' /home/brunhilde/OpenHub/.env /home/brunhilde/.config/openhub/bridge.env
```

Expected permissions for both environment files: `600`.

## Cloudflare tunnel checks

The existing public route is served by the existing `cloudflared.service`. Do not create a temporary `trycloudflare.com` tunnel for normal recovery.

```bash
systemctl --no-pager status cloudflared.service

# Management endpoint, when available locally.
curl -sS -m 3 http://127.0.0.1:20241/config
```

Expected ingress includes:

```text
hub.brunhilde.cloud -> http://127.0.0.1:7788
```

## Recovery patterns

### Public 502 or dashboard unavailable

1. Check local origin first:
   ```bash
   curl -sS -m 5 -i http://127.0.0.1:7788/v1/health/simple
   systemctl --user --no-pager status openhub-api.service
   ```
2. If local origin is down, inspect API logs:
   ```bash
   journalctl --user -u openhub-api.service -n 120 --no-pager
   ```
3. Restart the API only after preserving the current environment shape:
   ```bash
   systemctl --user restart openhub-api.service
   curl -sS -m 5 http://127.0.0.1:7788/v1/health/simple
   ```
4. Re-check the public route:
   ```bash
   curl -sS -m 8 https://hub.brunhilde.cloud/v1/health/simple
   ```

### Bridge process running but no fresh ACN heartbeat

1. Confirm the active bridge service:
   ```bash
   systemctl --user --no-pager status openhub-bridge-brunhilde.service
   journalctl --user -u openhub-bridge-brunhilde.service -n 120 --no-pager \
     | sed -E 's/(oh_)[A-Za-z0-9]+/\1[redacted]/g; s/(ak_)[A-Za-z0-9]+/\1[redacted]/g'
   ```
2. Confirm ACN status through the API:
   ```bash
   curl -sS -m 8 http://127.0.0.1:7788/v1/acn/status
   ```
3. If the legacy bridge is accidentally active, stop and disable it:
   ```bash
   systemctl --user stop openhub-bridge.service
   systemctl --user disable openhub-bridge.service
   ```
4. Restart only the intended bridge:
   ```bash
   systemctl --user restart openhub-bridge-brunhilde.service
   ```

### API healthy but ACN routes return 500

1. Compare local health and ACN:
   ```bash
   curl -sS -m 5 http://127.0.0.1:7788/v1/health/simple
   curl -sS -m 8 -i http://127.0.0.1:7788/v1/acn/status
   ```
2. Inspect recent API logs:
   ```bash
   journalctl --user -u openhub-api.service -n 160 --no-pager
   ```
3. If code works in tests but the live process is stale or poisoned, restart `openhub-api.service` and verify `/v1/health/simple`, `/v1/acn/status`, then the bridge heartbeat.

## Current known runtime observation

On 2026-05-26, the API and bridge were both healthy, but API logs showed repeated `heartbeat_check_failed` entries with `can't compare offset-naive and offset-aware datetimes`. The public and local health endpoints still returned HTTP 200, and the bridge continued sending heartbeats. Treat this as a release-verification follow-up before tagging if it persists.

## Release verification reminder

Before a release/tag decision, run the GSD verification gates from `.gsdrc.toml` plus live smoke:

```bash
. .venv/bin/activate && pytest -q --tb=short --disable-warnings
python scripts/check_dependency_drift.py
cd web && npm audit --audit-level=moderate
cd web && npm run lint -- --max-warnings=0
cd web && npm run typecheck
cd web && npm run test -- --run
cd web && npm run build
docker compose --env-file .env.example config >/tmp/openhub-compose-config.yml
curl -sS https://hub.brunhilde.cloud/v1/health/simple
curl -sS https://hub.brunhilde.cloud/v1/acn/status
```

The GitHub **OpenHub Release Verification** workflow is manual only (`workflow_dispatch`) and read-only (`contents: read`). It requires an explicit tag-shaped version that already matches `pyproject.toml`, refuses existing tags, builds Python distributions, runs `twine check`, builds the Docker image, and uploads artifacts to the workflow run. It does not create tags, create GitHub releases, push Docker images, or publish to PyPI/GHCR. Make any version bump and changelog update in a normal reviewed commit first, then create/push a tag only after an operator explicitly approves the release target.
