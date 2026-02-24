"""
Database connection and management for Agent Hub
"""
import sqlite3
import threading
from contextlib import contextmanager, asynccontextmanager
from pathlib import Path
from typing import Optional, Dict, Any, AsyncGenerator, Generator
import asyncio
import aiosqlite
from concurrent.futures import ThreadPoolExecutor

from ..config import get_settings
from ..logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class Database:
    """SQLite database manager with connection pooling"""
    
    def __init__(self, db_path: str, max_connections: int = 10):
        self.db_path = Path(db_path)
        self.max_connections = max_connections
        self._connection_pool: Optional[ThreadPoolExecutor] = None
        self._local = threading.local()
        self._lock = threading.Lock()
        
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info("database_initialized", db_path=str(self.db_path))
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, 'connection'):
            conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                isolation_level=None,  # Autocommit mode
                timeout=30.0
            )
            
            # Configure SQLite for optimal performance
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA cache_size = 10000")
            conn.execute("PRAGMA temp_store = MEMORY")
            conn.execute("PRAGMA mmap_size = 268435456")  # 256MB
            
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
    
    @contextmanager
    def get_sync_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get synchronous database connection"""
        conn = self._get_connection()
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error("database_error", error=str(e))
            raise
    
    @asynccontextmanager
    async def get_async_connection(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Get asynchronous database connection"""
        async with aiosqlite.connect(
            str(self.db_path),
            timeout=30.0
        ) as conn:
            # Configure connection
            await conn.execute("PRAGMA foreign_keys = ON")
            await conn.execute("PRAGMA journal_mode = WAL")
            await conn.execute("PRAGMA synchronous = NORMAL")
            await conn.execute("PRAGMA cache_size = 10000")
            await conn.execute("PRAGMA temp_store = MEMORY")
            
            # Set row factory
            conn.row_factory = aiosqlite.Row
            
            try:
                yield conn
            except Exception as e:
                await conn.rollback()
                logger.error("async_database_error", error=str(e))
                raise
    
    def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> sqlite3.Cursor:
        """Execute a query synchronously"""
        with self.get_sync_connection() as conn:
            if params:
                return conn.execute(query, params)
            else:
                return conn.execute(query)
    
    async def execute_async(self, query: str, params: Optional[Dict[str, Any]] = None) -> aiosqlite.Cursor:
        """Execute a query asynchronously"""
        async with self.get_async_connection() as conn:
            if params:
                cursor = await conn.execute(query, params)
            else:
                cursor = await conn.execute(query)
            await conn.commit()
            return cursor
    
    def fetch_one(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[sqlite3.Row]:
        """Fetch one row"""
        cursor = self.execute(query, params)
        return cursor.fetchone()
    
    async def fetch_one_async(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[aiosqlite.Row]:
        """Fetch one row asynchronously"""
        async with self.get_async_connection() as conn:
            if params:
                cursor = await conn.execute(query, params)
            else:
                cursor = await conn.execute(query)
            return await cursor.fetchone()
    
    def fetch_all(self, query: str, params: Optional[Dict[str, Any]] = None) -> list[sqlite3.Row]:
        """Fetch all rows"""
        cursor = self.execute(query, params)
        return cursor.fetchall()
    
    async def fetch_all_async(self, query: str, params: Optional[Dict[str, Any]] = None) -> list[aiosqlite.Row]:
        """Fetch all rows asynchronously"""
        async with self.get_async_connection() as conn:
            if params:
                cursor = await conn.execute(query, params)
            else:
                cursor = await conn.execute(query)
            return await cursor.fetchall()
    
    def execute_many(self, query: str, params_list: list[Dict[str, Any]]) -> None:
        """Execute query with multiple parameter sets"""
        with self.get_sync_connection() as conn:
            conn.executemany(query, params_list)
    
    async def execute_many_async(self, query: str, params_list: list[Dict[str, Any]]) -> None:
        """Execute query with multiple parameter sets asynchronously"""
        async with self.get_async_connection() as conn:
            await conn.executemany(query, params_list)
            await conn.commit()
    
    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Execute within a transaction"""
        with self.get_sync_connection() as conn:
            try:
                conn.execute("BEGIN")
                yield conn
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
    
    @asynccontextmanager
    async def async_transaction(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Execute within an async transaction"""
        async with self.get_async_connection() as conn:
            try:
                await conn.execute("BEGIN")
                yield conn
                await conn.execute("COMMIT")
            except Exception:
                await conn.execute("ROLLBACK")
                raise
    
    def get_table_info(self, table_name: str) -> list[sqlite3.Row]:
        """Get table schema information"""
        return self.fetch_all("PRAGMA table_info(?)", {"table_name": table_name})
    
    def get_table_list(self) -> list[str]:
        """Get list of all tables"""
        rows = self.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        return [row["name"] for row in rows]
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            # Database size
            db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
            
            # Table counts
            table_counts = {}
            for table in self.get_table_list():
                count_result = self.fetch_one(f"SELECT COUNT(*) as count FROM {table}")
                table_counts[table] = count_result["count"] if count_result else 0
            
            # WAL file size
            wal_path = self.db_path.with_suffix(".db-wal")
            wal_size = wal_path.stat().st_size if wal_path.exists() else 0
            
            return {
                "database_size_bytes": db_size,
                "wal_size_bytes": wal_size,
                "table_counts": table_counts,
                "database_path": str(self.db_path),
                "journal_mode": self.fetch_one("PRAGMA journal_mode")["journal_mode"],
                "page_size": self.fetch_one("PRAGMA page_size")["page_size"],
                "page_count": self.fetch_one("PRAGMA page_count")["page_count"]
            }
        except Exception as e:
            logger.error("database_stats_error", error=str(e))
            return {"error": str(e)}
    
    def vacuum(self) -> None:
        """Vacuum the database to reclaim space"""
        logger.info("database_vacuum_started")
        try:
            self.execute("VACUUM")
            logger.info("database_vacuum_completed")
        except Exception as e:
            logger.error("database_vacuum_failed", error=str(e))
            raise
    
    def checkpoint(self) -> None:
        """Checkpoint the WAL file"""
        try:
            result = self.fetch_one("PRAGMA wal_checkpoint(TRUNCATE)")
            if result:
                logger.debug("wal_checkpoint_completed", result=dict(result))
        except Exception as e:
            logger.warning("wal_checkpoint_failed", error=str(e))
    
    def close_all_connections(self) -> None:
        """Close all connections"""
        with self._lock:
            if hasattr(self._local, 'connection'):
                self._local.connection.close()
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