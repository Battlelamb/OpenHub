"""Stub from Wave 0 - implementations filled in by later plans.

End-to-end vector search against Turso. Marked turso so it skips on local dev
without credentials. Implementation lands in Plan 02 / Plan 05.
"""
import pytest


pytestmark = pytest.mark.turso


@pytest.mark.xfail(reason="Plan 02 implements vector roundtrip")
def test_roundtrip():
    assert False


@pytest.mark.xfail(reason="Plan 05 implements ranking")
def test_ranking():
    assert False


@pytest.mark.xfail(reason="Plan 02 implements DiskANN index creation")
def test_index_created():
    assert False
