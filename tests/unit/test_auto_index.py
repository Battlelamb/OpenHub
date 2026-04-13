"""Stub from Wave 0 - implementations filled in by later plans.

Auto-indexing tests cover the background scheduler that embeds rows after
write. Implementation lands in Plan 04 (auto-index orchestration).
"""
import pytest


@pytest.mark.xfail(reason="Plan 04 implements background indexing")
def test_background_task_scheduled():
    assert False


@pytest.mark.xfail(reason="Plan 04 implements background indexing")
def test_failed_status():
    assert False
