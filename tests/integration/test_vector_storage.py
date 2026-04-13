"""Stub from Wave 0 - implementations filled in by later plans.

Turso F32_BLOB roundtrip smoke test. Marked turso so it skips on local dev
without credentials. Implementation lands in Plan 02 (vector storage).
"""
import pytest


pytestmark = pytest.mark.turso


@pytest.mark.xfail(reason="Plan 02 implements (Turso smoke test)")
def test_binding_roundtrip():
    assert False
