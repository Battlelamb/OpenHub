# Phase 05-02 — Release-Readiness Snapshot

Generated: 2026-05-20 (GSD slice 05-02, OpenHub v1.0)
Method: verification-first — every claim below is backed by a command executed in this snapshot.

## State Summary

### Git
- Branch `master`, working tree clean (no uncommitted source changes at snapshot start).
- Recent commits (last 5):
  - `85b9a15` chore: initialize gsd claude operating loop
  - `07bd733` docs: adopt gsd workflow for openhub
  - `ff52b76` docs: add gastown benchmark notes
  - `a39b811` docs: inventory task lifecycle before evidence work
  - `9bde311` docs: record function-specific language boundaries
- Recent history is docs / GSD-setup only — no unreleased code changes pending.

### API Runtime — `GET http://localhost:7788/v1/health`
- Status **healthy**; version `0.1.0`; debug `false`; log level `INFO`.
- Database **ready** — `./data/state/agenthub.db` (~164 KB), connection ok.
- Artifact storage: present and writable.
- Cache (Redis): `not_implemented` — optional by design (graceful degradation).
- Load: 0/100 agents connected; 0 active / 0 queued tasks → no stale runtime work to recover.

### Tests / Build
| Surface | Command | Result |
|---|---|---|
| Backend | `.venv/bin/python -m pytest tests/ -x -q` | exit 0 — 183 passed, 10 skipped, 0 failed |
| Frontend typecheck | `npm run typecheck` (`tsc -b --noEmit`) | exit 0 — clean |
| Frontend tests | `npm test -- --run` (vitest) | exit 0 — 36/36 across 13 files |
| Frontend build | `npm run build` (`tsc -b && vite build`) | exit 0 — built in 3.91s |

Interpreter note: system `python3` (linuxbrew 3.14.3) has **no pytest** — the suite runs only via the project venv `.venv/bin/python` (3.13.5). Future snapshots must use the venv interpreter explicitly.

## Test Results

**Backend — PASS.** 193 tests collected: 183 passed, 10 skipped, 0 failed, 0 errors (pytest exit 0). Overall line coverage 55%.
- The 10 skips are environmental, not failures:
  - 9× vector search/storage integration tests — skipped: `Turso credentials not set` (vector search ships as opt-in beta; expected).
  - 1× `tests/unit/test_auth.py:120` — skipped: passlib/bcrypt backend rejects passwords longer than 72 bytes.

**Frontend — PASS.** TypeScript typecheck clean; 36/36 vitest tests pass across 13 files; production build succeeds.

**Runtime — PASS.** API healthy, DB connected, artifact storage writable.

Verified working: REST API boot + health, DB connectivity, the auth / agent / task / workflow / coordination / vector route suites (non-Turso paths), and the React command-center build with its component/hook tests.

Not verified in this snapshot: vector search against a live Turso DB (skipped), multi-agent live coordination, and the Claude-Code GSD execution loop (credential-gated — see Blocker 2).

## Blockers

Severity: CRITICAL (blocks release) / MEDIUM (fix before publishing) / LOW (tracked debt) / INFO.
**No CRITICAL code defects found.**

1. **MEDIUM — Duplicate OpenAPI `operationId`.** `list_workflows_v1_workflows__get` is emitted twice from `app/api/routes_workflow.py` (pytest UserWarning). It collides in the generated OpenAPI spec and `/docs`, breaking generated API clients. OpenHub v1.0's value prop includes a stable API contract — fix before the spec is published. Not a runtime fault.
2. **MEDIUM — GSD execution credential gate (process, not code).** `ANTHROPIC_API_KEY` / `CLAUDE_CODE_OAUTH_TOKEN` absent; `claude auth status` reports not logged in. Blocks the Claude-Code Opus operating loop — *not* the OpenHub release artifact itself. (Source: `05-CONTEXT.md`, `STATE.md`.)
3. **LOW — Pydantic v2 deprecations.** Class-based `Config` (`app/config.py:14`) and `min_items` / `max_items` (`app/models/agents.py:52`). Works on Pydantic 2.x; breaks on Pydantic V3.
4. **LOW — sqlite3 datetime adapter deprecation.** `app/database/connection.py:167` relies on the default datetime adapter, deprecated since Python 3.12. Works on 3.13; breaks on a future Python.
5. **LOW — Skipped auth test.** `test_auth.py:120` is skipped due to a passlib/bcrypt version mismatch (>72-byte password). It touches the auth path — pin compatible versions (or truncate input to 72 bytes) and un-skip.
6. **LOW — Frontend bundle size.** Single JS chunk 737.61 kB (220.21 kB gzip), over Vite's 500 kB warning; no code-splitting. Affects mobile-web load (a stated v1.0 target), not correctness.
7. **INFO — 9 vector-search tests skipped.** Turso credentials not set; vector search is opt-in beta, so that path is simply unverified in this snapshot.

## Recommended Next Actions

Prioritized:
1. **Fix the duplicate `operationId`** in `app/api/routes_workflow.py` — give the second `list_workflows` route an explicit unique `operation_id=`, or rename it; re-run pytest to confirm the warning clears. Small change, high value for the API-contract promise.
2. **Clear the credential gate** (operator action): export `ANTHROPIC_API_KEY` or run `claude auth login` so the GSD Opus loop can execute. No code change.
3. **Resolve the bcrypt/passlib skip**: pin compatible library versions (or truncate to 72 bytes) and un-skip `test_auth.py:120`.
4. **Docs freshness pass** (optional, quick): `CLAUDE.md` still lists Phase 2.3 / 2.4 as "Next Phases" and carries a Windows `D:\...` path, though phases 1–4 are complete (per `STATE.md`) and the runtime is Linux/WSL.
5. **Track deprecations** (Pydantic v2, sqlite3 adapter) as known debt; clear before a Pydantic 3 / newer-Python bump.
6. **Code-split the frontend bundle** (dynamic `import()` / `manualChunks`) — optional; improves mobile load time.
7. **Proceed to Slice 05-03 (Stuck Work Recovery UX)** once items 1–3 are addressed.

## Go/No-Go Assessment

**Verdict: GO (conditional).**

Evidence: backend 183/183 non-skipped tests green (pytest exit 0), frontend 36/36 green, typecheck and production build both succeed, API healthy with DB connected. No release-blocking code defects found; no architecture change required.

Conditions:
- Fix the duplicate `operationId` (Blocker 1) before the OpenAPI surface is published as a v1.0 contract.
- Clear the credential gate (Blocker 2) before any Claude-Code-driven GSD execution.
- Blockers 3–7 are tracked debt — they do not gate this snapshot or the next product slice.

Cleared to continue into release-prep work and Slice 05-03.

---

## Resolution Update — 2026-05-20

Follow-up slice closing Blockers 3 and 5 plus the docs-freshness recommendation.
Verification-first: claims below are backed by commands run in this slice.

### Blocker 3 (Pydantic v2 deprecations) — RESOLVED
- Class-based `Config` → `model_config`: `app/config.py` (`SettingsConfigDict`), `app/models/errors.py` (`ConfigDict`).
- `min_items`/`max_items` → `min_length`/`max_length`: `app/models/agents.py` (×2), `app/auth/models.py`, `app/models/tasks.py`, `app/api/routes_workflows.py`.
- The snapshot cited only two files; the actual sweep covered all 9 deprecation sites so the warnings fully clear.
- Evidence: pytest warnings summary now contains zero `PydanticDeprecated*` entries.

### Blocker 5 (skipped auth test) — RESOLVED
- Deeper than recorded: the ">72 bytes" error came from passlib 1.7.4's internal backend probe — passlib is unmaintained and cannot read bcrypt 5.x. "Truncate input" could not have fixed it, and `hash_password` was in fact broken for any fresh install.
- Fix: replaced passlib with the `bcrypt` library directly in `app/auth/jwt_auth.py` — the resolution already named in `02-websocket-test-suite/deferred-items.md`. `requirements.txt` and `pyproject.toml` now declare `bcrypt` instead of `passlib[bcrypt]`.
- `test_auth.py::test_password_hash_and_verify` un-skipped; `test_password_hash_handles_long_input` added to pin the 72-byte truncation path.

### Docs freshness — DONE
- `CLAUDE.md`: "Implementation Progress" realigned to the GSD roadmap (Phases 1-4 complete, Phase 5 in progress); Windows `D:\...` path replaced with the Linux path.
- `docs/PROJECT_ROADMAP.md`: marked SUPERSEDED with pointers to `.planning/ROADMAP.md` and `docs/ROADMAP_V2.md`.

### Evidence
- `.venv/bin/python -m pytest tests/ --no-cov` → exit 0, **185 passed, 9 skipped** (was 183 / 10; the 9 remaining skips are all Turso vector tests).

### Still open / newly flagged
- Unchanged from the snapshot: Blockers 1, 2, 4, 6, 7.
- New (flagged, not fixed): admin login in `app/api/routes_auth.py:291` uses a plaintext, non-constant-time `!=` password compare; `hash_password`/`verify_password` are imported there but unused. Candidate for a future hardening slice (`hmac.compare_digest`).
