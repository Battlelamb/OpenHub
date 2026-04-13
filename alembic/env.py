"""Alembic migration environment.

Reads the target database URL from the application Settings. When
``AGENTHUB_TURSO_DATABASE_URL`` is set, alembic routes migrations to Turso via
the ``sqlalchemy-libsql`` dialect so it talks to the same DB the application
uses at runtime. Otherwise it falls back to the local SQLite file at
``settings.db_path``.

The libSQL URL scheme is ``sqlite+libsql://<host>?secure=true``. The auth token
is passed via SQLAlchemy ``connect_args={"auth_token": ...}`` because the
``sqlalchemy-libsql`` 0.2.0 dialect does NOT auto-extract ``authToken`` from
the URL query (its ``create_connect_args`` only forwards a fixed allowlist of
pysqlite kwargs, and ``auth_token`` is not in it - leaving it in the URL
results in libsql_experimental ignoring it and Turso returning
``empty JWT token``).

The ``sqlalchemy-libsql`` package is required when Turso is configured; if
missing, we fail loud at startup rather than silently writing migrations to a
local file.
"""
from logging.config import fileConfig
from sqlalchemy import create_engine, pool
from alembic import context
import os
import sys
from urllib.parse import urlparse

# Add project root to path so app can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
from app.database.models import Base

# Alembic Config object
config = context.config


def _resolve_target(settings):
    """Return ``(sqlalchemy_url, connect_args)`` matching the runtime DB target.

    - When Turso is configured: returns ``("sqlite+libsql://<host>?secure=true",
      {"auth_token": <token>})``. Requires the ``sqlalchemy-libsql`` dialect.
    - Otherwise: returns ``("sqlite:///<local_path>", {})``.
    """
    turso_url = getattr(settings, "turso_database_url", None)
    turso_token = getattr(settings, "turso_auth_token", None)

    if turso_url and turso_token:
        try:
            import sqlalchemy_libsql  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "AGENTHUB_TURSO_DATABASE_URL is set but sqlalchemy-libsql is "
                "not installed. Install it on the deployment host: "
                "`pip install sqlalchemy-libsql`."
            ) from exc

        parsed = urlparse(turso_url)
        netloc = parsed.netloc or parsed.path
        sqlalchemy_url = f"sqlite+libsql://{netloc}?secure=true"
        connect_args = {"auth_token": turso_token}
        return sqlalchemy_url, connect_args

    return f"sqlite:///{settings.db_path}", {}


# Resolve target once at env.py import time so both online and offline modes
# see the same URL.
_settings = get_settings()
_sqlalchemy_url, _connect_args = _resolve_target(_settings)
config.set_main_option("sqlalchemy.url", _sqlalchemy_url)

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
    # Build the engine manually so we can pass connect_args (Turso auth_token).
    # engine_from_config doesn't expose connect_args via the alembic.ini key
    # space, and the sqlalchemy-libsql 0.2.0 dialect needs auth_token as a
    # connect kwarg, not a URL query parameter.
    connectable = create_engine(
        _sqlalchemy_url,
        poolclass=pool.NullPool,
        connect_args=_connect_args,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
