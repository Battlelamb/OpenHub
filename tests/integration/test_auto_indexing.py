"""Stub from Wave 0 - implementations filled in by later plans.

Verifies that writing a row schedules the background embedding task.
Implementation lands in Plan 04 (auto-indexing pipeline).
"""
import pytest


@pytest.mark.xfail(reason="Plan 04 implements auto-indexing")
def test_write_schedules_embedding():
    assert False
