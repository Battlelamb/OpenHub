"""Vector search availability predicate and FastAPI dependency.

Used by every vector-adjacent route to short-circuit cleanly on local SQLite
(per D-08: vector endpoints return 503 when Turso is not configured).

The predicate honours an explicit override via Settings.vector_search_enabled:

    - None  -> auto: enabled iff the database is in Turso mode
    - True  -> enabled iff the database is in Turso mode (cannot force-enable)
    - False -> always disabled
"""
from fastapi import HTTPException

from ..config import get_settings
from .connection import get_database


def is_vector_enabled() -> bool:
    """Return True when the vector search subsystem should accept traffic."""
    settings = get_settings()

    # Explicit disable always wins.
    if settings.vector_search_enabled is False:
        return False

    db = get_database()
    has_turso = bool(getattr(db, "_use_turso", False))

    # Explicit enable still requires Turso to be configured.
    if settings.vector_search_enabled is True:
        return has_turso

    # Auto mode: enabled iff Turso is configured.
    return has_turso


def require_vector() -> None:
    """FastAPI dependency: raise RFC 7807 503 if vector search unavailable."""
    if not is_vector_enabled():
        raise HTTPException(
            status_code=503,
            detail={
                "type": "https://openhub.dev/problems/vector-unavailable",
                "title": "Vector search unavailable",
                "status": 503,
                "detail": (
                    "Vector search requires Turso configuration. "
                    "Set AGENTHUB_TURSO_DATABASE_URL and AGENTHUB_TURSO_AUTH_TOKEN."
                ),
            },
        )
