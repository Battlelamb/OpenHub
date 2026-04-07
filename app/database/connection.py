"""
Database connection and management for Agent Hub
Supports both local SQLite and Turso (libSQL) with embedded replicas
"""
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Dict, Any, Generator
from concurrent.futures import ThreadPoolExecutor

from ..config import get_settings
from ..logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Try to import libsql for Turso support
try:
    import libsql_experimental as libsql
    TURSO_AVAILABLE = True
    logger.info("turso_libsql_available")
except ImportError:
    try:
        import libsql
        TURSO_AVAILABLE = True
        logger.info("turso_libsql_available")
    except ImportError:
        TURSO_AVAILABLE = False
        logger.info("turso_libsql_not_available_using_sqlite3")


class Database:
    """Database manager - Turso (libSQL) with SQLite fallback"""

    def __init__(self, db_path: str, max_connections: int = 10):
        self.db_path = Path(db_path)
        self.max_connections = max_connections
        self._connection_pool: Optional[ThreadPoolExecutor] = None
        self._local = threading.local()
        self._lock = threading.Lock()
        self._use_turso = False

        # Check if Turso is configured
        turso_url = getattr(settings, 'turso_database_url', None)
        turso_token = getattr(settings, 'turso_auth_token', None)

        if TURSO_AVAILABLE and turso_url and turso_token:
            self._use_turso = True
            self._turso_url = turso_url
            self._turso_token = turso_token
            logger.info("database_mode", mode="turso", sync_url=turso_url[:40] + "...")
        else:
            # Ensure database directory exists for local SQLite
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info("database_mode", mode="sqlite", db_path=str(self.db_path))

    def _get_connection(self):
        """Get thread-local database connection (Turso or SQLite)"""
        if not hasattr(self._local, 'connection'):
            if self._use_turso:
                # Use remote-only mode (no embedded replica issues)
                turso_url = self._turso_url
                if turso_url.startswith("libsql://"):
                    turso_url = turso_url.replace("libsql://", "https://")
                conn = libsql.connect(
                    turso_url,
                    auth_token=self._turso_token,
                )
                logger.debug("turso_remote_connected")
            else:
                conn = sqlite3.connect(
                    str(self.db_path),
                    check_same_thread=False,
                    isolation_level=None,
                    timeout=30.0,
                )
                # Configure SQLite for optimal performance
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("PRAGMA journal_mode = WAL")
                conn.execute("PRAGMA synchronous = NORMAL")
                conn.execute("PRAGMA cache_size = 10000")
                conn.execute("PRAGMA temp_store = MEMORY")

                # Enable JSON functions if available
                try:
                    conn.execute("SELECT json_extract('{}', '$')")
                    logger.debug("json_functions_enabled")
                except sqlite3.OperationalError:
                    logger.warning("json_functions_not_available")

                # Set row factory for dict-like access
                conn.row_factory = sqlite3.Row

            self._local.connection = conn
            logger.debug("connection_created", thread_id=threading.get_ident())

        return self._local.connection

    def sync(self) -> None:
        """No-op in remote mode. Sync only needed for embedded replicas."""
        pass

    @contextmanager
    def get_sync_connection(self) -> Generator:
        """Get synchronous database connection"""
        conn = self._get_connection()
        try:
            yield conn
        except Exception as e:
            if not self._use_turso:
                conn.rollback()
            logger.error("database_error", error=str(e))
            raise

    def _adapt_params(self, query: str, params: Optional[Dict[str, Any]] = None):
        """Convert named params (:key) to positional (?) for libsql compatibility"""
        if not params or not self._use_turso:
            return query, params

        import re
        from datetime import datetime as _dt

        # Convert unsupported types
        clean_params = {}
        for k, v in params.items():
            if isinstance(v, _dt):
                clean_params[k] = v.isoformat()
            elif isinstance(v, bool):
                clean_params[k] = 1 if v else 0
            elif v is None:
                clean_params[k] = None
            else:
                clean_params[k] = v

        # Find all :param_name in order
        param_names = re.findall(r':(\w+)', query)
        if not param_names:
            return query, clean_params

        # Replace :param_name with ? and build tuple
        new_query = re.sub(r':(\w+)', '?', query)
        param_tuple = tuple(clean_params.get(name) for name in param_names)
        return new_query, param_tuple

    def execute(self, query: str, params: Optional[Dict[str, Any]] = None):
        """Execute a query synchronously. Auto-commits and syncs for write operations."""
        with self.get_sync_connection() as conn:
            query, params = self._adapt_params(query, params)
            if params:
                cursor = conn.execute(query, params)
            else:
                cursor = conn.execute(query)

            # Auto-commit for write operations
            q = query.strip().upper()
            if q.startswith(("INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER")):
                try:
                    conn.commit()
                except Exception:
                    pass

            return cursor

    def fetch_one(self, query: str, params: Optional[Dict[str, Any]] = None):
        """Fetch one row"""
        cursor = self.execute(query, params)
        row = cursor.fetchone()
        if row and self._use_turso:
            # libsql returns tuples - convert to dict using cursor.description
            if cursor.description:
                cols = [d[0] for d in cursor.description]
                return dict(zip(cols, row))
        return row

    def fetch_all(self, query: str, params: Optional[Dict[str, Any]] = None):
        """Fetch all rows"""
        cursor = self.execute(query, params)
        rows = cursor.fetchall()
        if rows and self._use_turso and cursor.description:
            # libsql returns tuples - convert to dicts
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in rows]
        return rows

    def execute_many(self, query: str, params_list: list) -> None:
        """Execute query with multiple parameter sets"""
        with self.get_sync_connection() as conn:
            conn.executemany(query, params_list)

    @contextmanager
    def transaction(self) -> Generator:
        """Execute within a transaction"""
        with self.get_sync_connection() as conn:
            try:
                conn.execute("BEGIN")
                yield conn
                conn.execute("COMMIT")
                if self._use_turso:
                    self.sync()
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def get_table_list(self) -> list:
        """Get list of all tables"""
        rows = self.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        if self._use_turso:
            return [row["name"] for row in rows]
        return [row["name"] for row in rows]

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            table_counts = {}
            for table in self.get_table_list():
                count_result = self.fetch_one(f"SELECT COUNT(*) as count FROM {table}")
                table_counts[table] = count_result["count"] if count_result else 0

            return {
                "database_path": str(self.db_path),
                "mode": "turso" if self._use_turso else "sqlite",
                "table_counts": table_counts,
            }
        except Exception as e:
            logger.error("database_stats_error", error=str(e))
            return {"error": str(e)}

    def close_all_connections(self) -> None:
        """Close all connections"""
        with self._lock:
            if hasattr(self._local, 'connection'):
                try:
                    self._local.connection.close()
                except Exception:
                    pass
                delattr(self._local, 'connection')

        if self._connection_pool:
            self._connection_pool.shutdown(wait=True)
            self._connection_pool = None

        logger.info("database_connections_closed")


# Global database instance
_database: Optional[Database] = None
_database_lock = threading.Lock()


def get_database() -> Database:
    """Get global database instance"""
    global _database

    if _database is None:
        with _database_lock:
            if _database is None:
                _database = Database(settings.db_path)
                logger.info("global_database_initialized")

    return _database


def close_database() -> None:
    """Close global database instance"""
    global _database

    if _database is not None:
        with _database_lock:
            if _database is not None:
                _database.close_all_connections()
                _database = None
                logger.info("global_database_closed")
