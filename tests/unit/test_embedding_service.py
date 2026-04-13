"""Stub from Wave 0 - implementations filled in by later plans.

Embedding service tests cover provider selection (local vs openai), output
dimension contracts, and configuration validation. Implementation lands in
Plan 03 (embedding service module).
"""
import pytest


@pytest.mark.xfail(reason="Plan 03 implements embedding service")
def test_local_dim():
    from app.services.embedding_service import LocalEmbeddingBackend  # noqa: F401

    assert False


@pytest.mark.xfail(reason="Plan 03 implements embedding service")
def test_openai_dim_mocked():
    assert False


@pytest.mark.xfail(reason="Plan 03 implements embedding service")
def test_provider_selection_local():
    assert False


@pytest.mark.xfail(reason="Plan 03 implements embedding service")
def test_provider_selection_openai_missing_key():
    assert False


@pytest.mark.xfail(reason="Plan 03 implements embedding service")
def test_provider_selection_openai_present():
    assert False
