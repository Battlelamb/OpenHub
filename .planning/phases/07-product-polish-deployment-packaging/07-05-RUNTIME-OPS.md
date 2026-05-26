# Phase 07-05 Runtime Ops Cleanup Docs

Date: 2026-05-26T06:46:33Z
Slice: 07-05 — Runtime ops cleanup docs
Status: complete

## Objective

Document the real OpenHub runtime service layout and recovery checks without exposing secrets.

## Inputs checked

- `openhub-api.service` user service
- `openhub-bridge-brunhilde.service` user service
- disabled legacy `openhub-bridge.service`
- Cloudflare `cloudflared.service`
- local health endpoints on `127.0.0.1:7788`
- public health/dashboard endpoints on `hub.brunhilde.cloud`
- secret-file permissions for `/home/brunhilde/OpenHub/.env` and `/home/brunhilde/.config/openhub/bridge.env`
- GSD planning state and Phase 07 plan

## Verified runtime truth

| Item | Result |
|---|---|
| Git state | clean before slice; local/origin/remote all at `0de91ad6ca30abbf29c38234a29c68251bbc7556` |
| GSD config parse | `.planning/config.json`, `.gsd/provider-config.json`, `.claude/settings.json`, `.gsdrc.toml` parse OK |
| GSD compatibility health | `node .codex/get-shit-done/bin/gsd-tools.cjs validate health` returned `healthy` |
| GSD compatibility consistency | passed with 5 non-blocking planning warnings |
| Secret scan | focused scan over GSD/config surfaces returned none after boundary-safe pattern |
| API service | `openhub-api.service` enabled + active |
| API command | `.venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 7788` |
| Bridge service | `openhub-bridge-brunhilde.service` enabled + active |
| Bridge command | `.venv/bin/python3 scripts/run_bridge.py --agent brunhilde --hub http://localhost:7788 --heartbeat 60` |
| Legacy bridge | `openhub-bridge.service` disabled + inactive |
| Env permissions | `.env` and bridge env both `600` |
| Cloudflare service | `cloudflared.service` active |
| Tunnel route | `hub.brunhilde.cloud -> http://127.0.0.1:7788` |
| Local `/v1/health/simple` | HTTP 200 |
| Public `/v1/health/simple` | HTTP 200 |
| Local `/v1/acn/status` | HTTP 200; payload reported 5 agents |
| Public `/v1/acn/status` | HTTP 200; payload reported 5 agents |
| Dashboard routes | `/dashboard`, `/dashboard/tasks`, `/dashboard/agents`, `/dashboard/health` all HTTP 200 |

## Files changed

- Created `docs/OPERATIONS.md` with secret-safe diagnostics, recovery checks, service truth, and release verification reminder.
- Updated `README.md` to link the operations runbook.
- Updated `.planning/STATE.md` and `.planning/ROADMAP.md` to reflect 07-05 completion and current live truth.

## Notes

The live API logs contained repeated `heartbeat_check_failed` messages:

```text
can't compare offset-naive and offset-aware datetimes
```

The API and bridge were still active, `/v1/health/simple` returned HTTP 200 locally and publicly, and the bridge continued sending heartbeats. This is recorded in `docs/OPERATIONS.md` as a release-verification follow-up before tagging if it persists.

## Verification commands run

```bash
git status --short --branch
git remote -v
git log --oneline --decorate -6
python3 - <<'PY'
import json, pathlib, tomllib
for p in ['.planning/config.json','.gsd/provider-config.json','.claude/settings.json']:
    json.loads(pathlib.Path(p).read_text())
tomllib.loads(pathlib.Path('.gsdrc.toml').read_text())
PY
node .codex/get-shit-done/bin/gsd-tools.cjs validate health
node .codex/get-shit-done/bin/gsd-tools.cjs validate consistency
systemctl --user --no-pager --plain status openhub-api.service openhub-bridge-brunhilde.service openhub-bridge.service
curl -sS -m 5 http://127.0.0.1:7788/v1/health/simple
curl -sS -m 8 http://127.0.0.1:7788/v1/acn/status
curl -sS -m 8 https://hub.brunhilde.cloud/v1/health/simple
curl -sS -m 12 https://hub.brunhilde.cloud/v1/acn/status
for path in /dashboard /dashboard/tasks /dashboard/agents /dashboard/health; do
  curl -sS -o /dev/null -m 8 -w '%{http_code}\n' "https://hub.brunhilde.cloud$path"
done
stat -c '%a %U:%G %n' /home/brunhilde/OpenHub/.env /home/brunhilde/.config/openhub/bridge.env
systemctl --no-pager --plain status cloudflared.service
curl -sS -m 3 http://127.0.0.1:20241/config
```

## GSD artifact reconciliation

The compatibility GSD `progress table` currently reports `32/36 plans (89%)` because several super-plan files do not have matching `SUMMARY.md` files. The curated planning truth in `.planning/STATE.md` and `.planning/ROADMAP.md` tracks Phase 07 slices directly and now marks 07-05 complete. Treat the raw progress table as artifact-count telemetry, not final phase truth.

## Next slice

07-06 — Full verification + tag decision.
