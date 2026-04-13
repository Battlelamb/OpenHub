"""Tests for app.database.vector_availability.

The vector feature flag is the foundation that every Phase 3 plan layers on
top of: routes call require_vector() to return RFC 7807 503 when Turso is not
configured, and is_vector_enabled() is the single source of truth.
"""
import pytest
from fastapi import HTTPException

from app.database import vector_availability
from app.database.vector_availability import is_vector_enabled, require_vector


class _FakeDb:
    def __init__(self, use_turso: bool):
        self._use_turso = use_turso


class _FakeSettings:
    def __init__(self, vector_search_enabled):
        self.vector_search_enabled = vector_search_enabled


@pytest.fixture()
def patch_env(monkeypatch):
    def _apply(use_turso: bool, vector_search_enabled=None):
        monkeypatch.setattr(
            vector_availability,
            "get_database",
            lambda: _FakeDb(use_turso=use_turso),
        )
        monkeypatch.setattr(
            vector_availability,
            "get_settings",
            lambda: _FakeSettings(vector_search_enabled=vector_search_enabled),
        )

    return _apply


def test_is_vector_enabled_false_on_sqlite(patch_env):
    patch_env(use_turso=False, vector_search_enabled=None)
    assert is_vector_enabled() is False


def test_is_vector_enabled_true_when_turso_auto(patch_env):
    patch_env(use_turso=True, vector_search_enabled=None)
    assert is_vector_enabled() is True


def test_require_vector_raises_503(patch_env):
    patch_env(use_turso=False, vector_search_enabled=None)
    with pytest.raises(HTTPException) as exc_info:
        require_vector()
    assert exc_info.value.status_code == 503
    detail = exc_info.value.detail
    assert isinstance(detail, dict)
    assert "vector search requires Turso".lower() in str(detail).lower()


def test_feature_flag_explicit_false_overrides(patch_env):
    # Even with Turso configured, an explicit False disables vector search.
    patch_env(use_turso=True, vector_search_enabled=False)
    assert is_vector_enabled() is False
    with pytest.raises(HTTPException):
        require_vector()


def test_feature_flag_explicit_true_without_turso_still_false(patch_env):
    # Cannot force-enable without Turso configured.
    patch_env(use_turso=False, vector_search_enabled=True)
    assert is_vector_enabled() is False


# Plan 06: full coverage of all (Turso, flag) combinations.


def test_explicit_false_overrides_turso(patch_env):
    """Even with Turso configured, explicit False disables vector search."""
    patch_env(use_turso=True, vector_search_enabled=False)
    assert is_vector_enabled() is False


def test_true_without_turso_still_false(patch_env):
    """Explicit True cannot force-enable without a real Turso connection."""
    patch_env(use_turso=False, vector_search_enabled=True)
    assert is_vector_enabled() is False


def test_none_auto_detects_turso(patch_env):
    """None means auto: enabled when Turso is configured."""
    patch_env(use_turso=True, vector_search_enabled=None)
    assert is_vector_enabled() is True


def test_none_auto_detects_no_turso(patch_env):
    """None means auto: disabled on local SQLite."""
    patch_env(use_turso=False, vector_search_enabled=None)
    assert is_vector_enabled() is False
