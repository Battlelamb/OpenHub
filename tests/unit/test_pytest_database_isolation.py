"""Regression guard: the normal pytest suite must not use live Turso."""

from app.config import get_settings
from app.database.connection import get_database


def test_pytest_uses_isolated_sqlite_database_by_default() -> None:
    settings = get_settings()

    assert settings.turso_database_url in (None, "")
    assert settings.turso_auth_token in (None, "")
    assert "openhub-test-db-" in settings.db_path

    info = get_database().get_database_stats()
    assert info["mode"] == "sqlite"
    assert "openhub-test-db-" in info["database_path"]
