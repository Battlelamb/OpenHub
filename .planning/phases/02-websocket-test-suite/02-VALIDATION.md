---
phase: 02
slug: websocket-test-suite
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 02 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 with pytest-asyncio 0.21.1 |
| **Config file** | pyproject.toml |
| **Quick run command** | `.venv/bin/python -m pytest tests/ -x -q --tb=short` |
| **Full suite command** | `.venv/bin/python -m pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/ -x -q --tb=short`
- **After every plan wave:** Run `.venv/bin/python -m pytest tests/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-00-01 | 00 | 0 | TEST-01..05 | scaffold | `.venv/bin/python -m pytest tests/ -x -q` | W0 | pending |
| 02-01-01 | 01 | 1 | WS-02 | unit | `.venv/bin/python -m pytest tests/unit/test_connection_manager.py -v` | W0 | pending |
| 02-02-01 | 02 | 1 | WS-01 | integration | `.venv/bin/python -m pytest tests/integration/test_websocket.py -v` | W0 | pending |
| 02-03-01 | 03 | 2 | WS-04,WS-05 | integration | `.venv/bin/python -m pytest tests/integration/test_ws_events.py -v` | W0 | pending |
| 02-04-01 | 04 | 2 | TEST-01 | unit | `.venv/bin/python -m pytest tests/unit/test_auth.py -v` | W0 | pending |
| 02-05-01 | 05 | 3 | TEST-02 | unit | `.venv/bin/python -m pytest tests/unit/test_capability_matcher.py -v` | W0 | pending |
| 02-06-01 | 06 | 3 | TEST-03,TEST-04 | integration | `.venv/bin/python -m pytest tests/integration/test_task_lifecycle.py -v` | W0 | pending |

*Status: pending - awaiting planning*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` - Update admin_headers fixture to generate real JWT
- [ ] `tests/unit/test_connection_manager.py` - Stub for WS-02
- [ ] `tests/integration/test_websocket.py` - Stub for WS-01, TEST-05
- [ ] `tests/unit/test_auth.py` - Stub for TEST-01
- [ ] `tests/unit/test_capability_matcher.py` - Stub for TEST-02
- [ ] `tests/integration/test_task_lifecycle.py` - Stub for TEST-03, TEST-04
- [ ] `tests/integration/test_ws_events.py` - Stub for WS-04, WS-05

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dashboard WS auth via initial frame | WS-01 | Visual verification of no token in URL/logs | Connect browser WS, check server logs for token absence |
| Agent status change latency < 1s | WS-04 | Timing-sensitive real-time behavior | Register agent, stop heartbeat, measure broadcast latency |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
