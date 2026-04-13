"""Stub from Wave 0 - implementations filled in by later plans.

Retry worker picks up rows where embedding_status='failed' after a backoff.
Implementation lands in Plan 04 (retry worker).
"""
import pytest


@pytest.mark.xfail(reason="Plan 04 implements retry worker")
def test_retry_picks_up_failed_rows():
    assert False
