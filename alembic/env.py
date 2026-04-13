"""Alembic migration environment.

Reads the target database URL from the application Settings. When
``AGENTHUB_TURSO_DATABASE_URL`` is set, we route migrations to Turso via the
``sqlalchemy-libsql`` dialect so alembic talks to the same DB the application
uses at runtime. Otherwise we fall back to the local SQLite file at
``settings.db_path``.

The libSQL URL scheme is ``sqlite+libsql://<host>?authToken=<token>&secure=true``.
The ``sqlalchemy-libsql`` package (pip: ``sqlalchemy-libsql``) registers this
dialect; if it's not installed and Turso is configured, we fail loud so the
deploy is caught early rather than silently writing migrations to a local file.
"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys
from urllib.parse import urlencode, urlparse

# Add project root to path so app can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
from app.database.models import Base

# Alembic Config object
config = context.config


def _build_sqlalchemy_url(settings) -> str:
    """Return a SQLAlchemy URL matching the runtime DB target.

    - When Turso is configured, return
      ``sqlite+libsql://<host>?authToken=...&secure=true`` and require the
      ``sqlalchemy-libsql`` dialect to be importable.
    - Otherwise, return ``sqlite:///<local_path>``.
    """
    turso_url = getattr(settings, "turso_database_url", None)
    turso_token = getattr(settings, "turso_auth_token", None)

    if turso_url and turso_token:
        # Validate the dialect is installed so we don't silently fall back
        # to local SQLite. Failing here surfaces the missing dep at startup.
        try:
            import sqlalchemy_libsql  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "AGENTHUB_TURSO_DATABASE_URL is set but sqlalchemy-libsql is "
                "not installed. Install it on the deployment host: "
                "`pip install sqlalchemy-libsql`."
            ) from exc

        # Convert libsql://host to sqlite+libsql://host?authToken=...&secure=true
        parsed = urlparse(turso_url)
        netloc = parsed.netloc or parsed.path
        query = urlencode({"authToken": turso_token, "secure": "true"})
        return f"sqlite+libsql://{netloc}?{query}"

    return f"sqlite:///{settings.db_path}"


# Override sqlalchemy.url from app Settings (Turso-aware).
settings = get_settings()
config.set_main_option("sqlalchemy.url", _build_sqlalchemy_url(settings))

# Setup logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
