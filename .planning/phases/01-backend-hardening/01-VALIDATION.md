---
phase: 1
slug: backend-hardening
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-07
---

# Phase 1 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x with pytest-asyncio |
| **Config file** | `pyproject.toml` (pytest section exists) |
| **Quick run command** | `python -m pytest tests/ -x -q --tb=short` |
| **Full suite command** | `python -m pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q --tb=short`
- **After every plan wave:** Run `python -m pytest tests/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | HARD-01 | integration | `pytest tests/ -k auth` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | HARD-02 | unit | `pytest tests/ -k admin` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | HARD-03 | unit | `pytest tests/ -k capabilities` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | HARD-04 | integration | `pytest tests/ -k heartbeat` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | HARD-07 | integration | `curl localhost:7788/docs` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending / ✅ green / ❌ red / ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` - shared fixtures (test DB, test client, test API keys)
- [ ] `tests/unit/` - directory for unit tests
- [ ] `tests/integration/` - directory for integration tests

*Existing infrastructure: pytest + pytest-asyncio + httpx already in requirements.txt*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Server refuses to start without admin env vars | HARD-02 | Requires process lifecycle check | Set no AGENTHUB_ADMIN_USER, run uvicorn, verify exit with error |
| CORS rejects unauthorized origins | HARD-05 | Requires browser-like request | curl with Origin header, verify rejection |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
